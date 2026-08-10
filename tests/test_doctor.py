import sqlite3
import tempfile
import unittest
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cli.doctor import (
    CheckStatus,
    DoctorCheck,
    DoctorReport,
    DoctorRunner,
    _metadata_errors,
    _parse_docker_timestamp,
    find_tracked_secret_paths,
    validate_configuration,
    validate_network_topology,
)


class StubConfig:
    def __init__(self, values, config_path):
        self._values = values
        self.config_path = Path(config_path)

    def get(self, key, default=None):
        value = self._values
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value


def valid_configuration():
    return {
        "app": {
            "environment": "production",
            "version": "1.0.0",
        },
        "paths": {
            "storage_dir": "./storage",
            "campaigns_dir": "./storage/campaigns",
            "certs_dir": "./certs",
            "docker_compose": "./server/docker-compose.yml",
            "docker_compose_dev": "./server/docker-compose-dev.yml",
            "env_file": "./server/.env",
        },
        "sessions": {
            "max_active": 20,
            "token_ttl_seconds": 300,
            "handshake_timeout_seconds": 10,
            "startup_timeout_seconds": 45,
            "rate_limit_window_seconds": 60,
            "max_attempts_per_client": 10,
            "max_attempts_global": 200,
        },
        "docker": {
            "images": {
                "victim": {
                    "name": "victim:latest",
                    "context": "./images",
                    "dockerfile": "./images/Dockerfile",
                }
            }
        },
        "ssl": {
            "dns_challenge": {
                "provider": "duckdns",
                "credentials": ["DUCKDNS_TOKEN"],
            }
        },
    }


def valid_compose_topology():
    socket_mount = {
        "type": "bind",
        "source": "/var/run/docker.sock",
        "target": "/var/run/docker.sock",
        "read_only": True,
    }
    return {
        "services": {
            "frontend": {
                "networks": {"bitm-dashboard": None},
                "ports": [
                    {
                        "host_ip": "127.0.0.1",
                        "published": "8443",
                        "target": 443,
                    }
                ],
            },
            "backend": {
                "networks": {
                    "bitm-network": None,
                    "bitm-dashboard": None,
                    "docker-control": None,
                }
            },
            "traefik": {
                "networks": {
                    "bitm-network": None,
                    "traefik-control": None,
                }
            },
            "docker-proxy": {
                "networks": {"docker-control": None},
                "volumes": [socket_mount],
            },
            "traefik-docker-proxy": {
                "networks": {"traefik-control": None},
                "volumes": [socket_mount],
            },
        },
        "networks": {
            "bitm-network": {},
            "bitm-dashboard": {},
            "docker-control": {"internal": True},
            "traefik-control": {"internal": True},
        },
    }


class ConfigurationValidationTests(unittest.TestCase):
    def test_accepts_supported_production_configuration(self):
        self.assertEqual(validate_configuration(valid_configuration()), [])

    def test_rejects_unsafe_session_and_dns_settings(self):
        values = valid_configuration()
        values["sessions"]["token_ttl_seconds"] = 5
        values["ssl"]["dns_challenge"]["credentials"] = ["INVALID-NAME"]

        errors = validate_configuration(values)

        self.assertTrue(
            any("token_ttl_seconds" in error for error in errors)
        )
        self.assertTrue(
            any("credential variable names" in error for error in errors)
        )


class NetworkTopologyTests(unittest.TestCase):
    def test_accepts_isolated_one_host_topology(self):
        self.assertEqual(
            validate_network_topology(valid_compose_topology()),
            [],
        )

    def test_rejects_published_socket_proxy_and_non_internal_control_network(self):
        compose = valid_compose_topology()
        compose["services"]["docker-proxy"]["ports"] = ["2375:2375"]
        compose["networks"]["docker-control"]["internal"] = False

        errors = validate_network_topology(compose)

        self.assertTrue(
            any("docker-control must be declared" in error for error in errors)
        )
        self.assertTrue(
            any("docker-proxy must not publish" in error for error in errors)
        )


class TrackedSecretTests(unittest.TestCase):
    def test_detects_runtime_secrets_and_allows_examples(self):
        tracked = find_tracked_secret_paths(
            [
                ".env.example",
                "server/.env",
                "server/.secrets/dns/DUCKDNS_TOKEN",
                "storage/p-bitm.db",
                "docs/example.txt",
            ]
        )

        self.assertEqual(
            tracked,
            [
                "server/.env",
                "server/.secrets/dns/DUCKDNS_TOKEN",
                "storage/p-bitm.db",
            ],
        )


class DnsSecretTests(unittest.TestCase):
    def test_reports_secret_state_without_exposing_credential_value(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            secrets_directory = root / "server" / ".secrets" / "dns"
            secrets_directory.mkdir(parents=True, mode=0o700)
            secrets_directory.chmod(0o700)
            credential = secrets_directory / "DUCKDNS_TOKEN"
            secret_value = "private-token-value"
            credential.write_text(f"{secret_value}\n")
            credential.chmod(0o600)
            dns_environment = root / "server" / ".traefik-dns.env"
            dns_environment.write_text(
                "DUCKDNS_TOKEN_FILE=/run/secrets/dns/DUCKDNS_TOKEN\n"
            )
            dns_environment.chmod(0o600)
            runtime = root / "server" / "traefik" / "runtime.yml"
            runtime.parent.mkdir()
            runtime.write_text("entryPoints: {}\n")
            config_path = root / "config.yaml"
            config_path.write_text("{}")
            config = StubConfig(
                {
                    "app": {"environment": "production"},
                    "ssl": {
                        "dns_challenge": {
                            "provider": "duckdns",
                            "credentials": ["DUCKDNS_TOKEN"],
                        }
                    },
                    "paths": {
                        "dns_secrets_dir": str(secrets_directory),
                        "traefik_dns_env_file": str(dns_environment),
                        "traefik_prod_runtime": str(runtime),
                    },
                },
                config_path,
            )
            runner = DoctorRunner(config, project_root=root)

            runner._check_dns_secrets()

            self.assertEqual(runner.checks[0].status, CheckStatus.PASS)
            self.assertNotIn(secret_value, runner.checks[0].detail)


class DoctorReportTests(unittest.TestCase):
    def test_strict_mode_treats_warnings_as_blocking(self):
        checks = (
            DoctorCheck("ready", CheckStatus.PASS, "ok"),
            DoctorCheck("profile", CheckStatus.WARN, "development"),
        )

        self.assertTrue(DoctorReport(checks, strict=False).healthy)
        self.assertFalse(DoctorReport(checks, strict=True).healthy)

    def test_parses_nanosecond_docker_timestamp_on_python_39(self):
        parsed = _parse_docker_timestamp(
            "2026-07-26T14:03:32.245931631Z"
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.microsecond, 245931)


class DatabaseIntegrityTests(unittest.TestCase):
    def test_checks_sqlite_database_in_read_only_mode(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "storage" / "p-bitm.db"
            database.parent.mkdir()
            connection = sqlite3.connect(database)
            connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
            connection.commit()
            connection.close()
            config_path = root / "config.yaml"
            config_path.write_text("{}")
            config = StubConfig(
                {"database": {"path": str(database)}},
                config_path,
            )
            runner = DoctorRunner(config, project_root=root)

            runner._check_database()

            self.assertEqual(len(runner.checks), 1)
            self.assertEqual(runner.checks[0].status, CheckStatus.PASS)
            self.assertFalse(database.with_name("p-bitm.db-journal").exists())

    def test_rejects_database_with_host_incompatible_mode(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "storage" / "p-bitm.db"
            database.parent.mkdir()
            database.write_bytes(b"not inspected when metadata is unsafe")
            database.chmod(0o600)
            config_path = root / "config.yaml"
            config_path.write_text("{}")
            config = StubConfig(
                {"database": {"path": str(database)}},
                config_path,
            )
            runner = DoctorRunner(config, project_root=root)

            runner._check_database()

            self.assertEqual(runner.checks[0].status, CheckStatus.FAIL)
            self.assertIn("permissions must be 0644", runner.checks[0].detail)


class HostMetadataTests(unittest.TestCase):
    def test_detects_unexpected_owner_uid(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "runtime.env"
            path.write_text("VALUE=secret\n")
            path.chmod(0o600)
            actual_uid = path.stat().st_uid

            errors = _metadata_errors(
                path,
                "runtime.env",
                actual_uid + 1,
                0o600,
            )

            self.assertTrue(any("owner UID" in error for error in errors))

    def test_storage_requires_host_readable_0755_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            storage = root / "storage"
            campaigns = storage / "campaigns"
            for directory in (storage, campaigns):
                directory.mkdir(exist_ok=True)
                directory.chmod(0o755)
            config_path = root / "config.yaml"
            config_path.write_text("{}")
            config = StubConfig(
                {
                    "paths": {
                        "storage_dir": str(storage),
                        "campaigns_dir": str(campaigns),
                    }
                },
                config_path,
            )
            runner = DoctorRunner(config, project_root=root)

            with patch(
                "cli.doctor.shutil.disk_usage",
                return_value=SimpleNamespace(free=15 * 1024**3),
            ):
                runner._check_storage()

            self.assertEqual(runner.checks[0].status, CheckStatus.PASS)

            campaigns.chmod(0o775)
            runner.checks.clear()
            with patch(
                "cli.doctor.shutil.disk_usage",
                return_value=SimpleNamespace(free=15 * 1024**3),
            ):
                runner._check_storage()

            self.assertEqual(runner.checks[0].status, CheckStatus.FAIL)
            self.assertIn("permissions must be 0755", runner.checks[0].detail)


if __name__ == "__main__":
    unittest.main()
