"""Read-only preflight checks for local P-BitM releases and deployments."""

from __future__ import annotations

import ipaddress
import json
import os
import platform
import re
import shutil
import sqlite3
import ssl
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import docker
import yaml

from cli import __version__
from cli.runtime_env import get_runtime_env_errors, read_env_file
from cli.utils import (
    MIN_DOCKER_ENGINE_VERSION,
    docker_buildkit_is_disabled,
    docker_engine_is_supported,
    get_docker_buildx_version,
    get_docker_compose_version,
)


MIN_FREE_STORAGE_BYTES = 5 * 1024**3
CRITICAL_FREE_STORAGE_BYTES = 1 * 1024**3
MIN_CERTIFICATE_DAYS = 30
SOURCE_EXCLUDES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "node_modules",
    "storage",
}


class CheckStatus(str, Enum):
    """Possible outcomes for a preflight check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class DoctorCheck:
    """One sanitized preflight result."""

    name: str
    status: CheckStatus
    detail: str
    action: str = ""

    def to_dict(self) -> dict[str, str]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass(frozen=True)
class DoctorReport:
    """Complete preflight report with release-gate semantics."""

    checks: tuple[DoctorCheck, ...]
    strict: bool = False

    @property
    def healthy(self) -> bool:
        blocking = {CheckStatus.FAIL}
        if self.strict:
            blocking.add(CheckStatus.WARN)
        return not any(check.status in blocking for check in self.checks)

    @property
    def summary(self) -> dict[str, int]:
        return {
            status.value: sum(
                check.status == status
                for check in self.checks
            )
            for status in CheckStatus
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "strict": self.strict,
            "summary": self.summary,
            "checks": [check.to_dict() for check in self.checks],
        }


def validate_configuration(values: Any) -> list[str]:
    """Return configuration errors without applying default values."""
    if not isinstance(values, dict):
        return ["configuration root must be a mapping"]

    errors = []
    app = values.get("app")
    if not isinstance(app, dict):
        errors.append("app must be a mapping")
    else:
        if app.get("environment") not in {"development", "production"}:
            errors.append("app.environment must be development or production")
        if not isinstance(app.get("version"), str) or not app.get("version", "").strip():
            errors.append("app.version must be a non-empty string")

    paths = values.get("paths")
    required_paths = {
        "storage_dir",
        "campaigns_dir",
        "certs_dir",
        "docker_compose",
        "docker_compose_dev",
        "env_file",
    }
    if not isinstance(paths, dict):
        errors.append("paths must be a mapping")
    else:
        missing_paths = sorted(
            name for name in required_paths
            if not isinstance(paths.get(name), str) or not paths[name].strip()
        )
        if missing_paths:
            errors.append(f"missing path settings: {', '.join(missing_paths)}")

    sessions = values.get("sessions")
    session_ranges = {
        "max_active": (1, 1_000),
        "token_ttl_seconds": (60, 86_400),
        "handshake_timeout_seconds": (1, 300),
        "startup_timeout_seconds": (5, 600),
        "rate_limit_window_seconds": (1, 3_600),
        "max_attempts_per_client": (1, 10_000),
        "max_attempts_global": (1, 100_000),
    }
    if not isinstance(sessions, dict):
        errors.append("sessions must be a mapping")
    else:
        for name, (minimum, maximum) in session_ranges.items():
            value = sessions.get(name)
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"sessions.{name} must be an integer")
            elif not minimum <= value <= maximum:
                errors.append(
                    f"sessions.{name} must be between {minimum} and {maximum}"
                )

    docker_config = values.get("docker")
    if not isinstance(docker_config, dict):
        errors.append("docker must be a mapping")
    elif not isinstance(docker_config.get("images"), dict):
        errors.append("docker.images must be a mapping")
    else:
        for key, image in docker_config["images"].items():
            if not isinstance(image, dict):
                errors.append(f"docker.images.{key} must be a mapping")
                continue
            if image.get("enabled", True) and not image.get("name"):
                errors.append(f"docker.images.{key}.name is required")
            if image.get("enabled", True) and not image.get("context"):
                errors.append(f"docker.images.{key}.context is required")
            has_single = bool(image.get("dockerfile"))
            has_arch = bool(
                image.get("dockerfile_amd64")
                and image.get("dockerfile_arm64")
            )
            if image.get("enabled", True) and not (has_single or has_arch):
                errors.append(
                    f"docker.images.{key} requires a Dockerfile setting"
                )

    if isinstance(app, dict) and app.get("environment") == "production":
        ssl_config = values.get("ssl")
        challenge = (
            ssl_config.get("dns_challenge")
            if isinstance(ssl_config, dict)
            else None
        )
        if not isinstance(challenge, dict):
            errors.append("ssl.dns_challenge must be a mapping in production")
        else:
            provider = challenge.get("provider")
            if not isinstance(provider, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]+",
                provider,
            ):
                errors.append("ssl.dns_challenge.provider is invalid")
            credentials = challenge.get("credentials")
            if not isinstance(credentials, list) or not credentials:
                errors.append(
                    "ssl.dns_challenge.credentials must be a non-empty list"
                )
            elif any(
                not isinstance(name, str)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
                for name in credentials
            ):
                errors.append("DNS credential variable names are invalid")

    return errors


def validate_network_topology(compose: Any) -> list[str]:
    """Validate the one-host isolation boundaries declared by Compose."""
    if not isinstance(compose, dict):
        return ["Compose output is not a mapping"]
    services = compose.get("services")
    networks = compose.get("networks")
    if not isinstance(services, dict) or not isinstance(networks, dict):
        return ["Compose must define services and networks"]

    errors = []
    for network in ("docker-control", "traefik-control"):
        definition = networks.get(network)
        if not isinstance(definition, dict) or definition.get("internal") is not True:
            errors.append(f"{network} must be declared as an internal network")

    expected_memberships = {
        "frontend": {"bitm-dashboard"},
        "backend": {"bitm-network", "bitm-dashboard", "docker-control"},
        "traefik": {"bitm-network", "traefik-control"},
        "docker-proxy": {"docker-control"},
        "traefik-docker-proxy": {"traefik-control"},
    }
    for service_name, expected in expected_memberships.items():
        service = services.get(service_name)
        if not isinstance(service, dict):
            errors.append(f"missing Compose service: {service_name}")
            continue
        actual = _service_network_names(service)
        if actual != expected:
            errors.append(
                f"{service_name} networks must be "
                f"{', '.join(sorted(expected))}"
            )

    for service_name in ("backend", "docker-proxy", "traefik-docker-proxy"):
        service = services.get(service_name)
        if isinstance(service, dict) and service.get("ports"):
            errors.append(f"{service_name} must not publish host ports")

    frontend = services.get("frontend")
    if isinstance(frontend, dict):
        published = frontend.get("ports") or []
        if not _has_loopback_port(published, 8443):
            errors.append("frontend port 8443 must bind only to 127.0.0.1")

    for service_name in ("docker-proxy", "traefik-docker-proxy"):
        service = services.get(service_name)
        if isinstance(service, dict) and not _has_read_only_docker_socket(service):
            errors.append(
                f"{service_name} must mount the Docker socket read-only"
            )

    return errors


def find_tracked_secret_paths(paths: Iterable[str]) -> list[str]:
    """Return tracked paths that should never be committed."""
    unsafe = []
    secret_suffixes = {
        ".db",
        ".jks",
        ".key",
        ".keystore",
        ".p12",
        ".pem",
        ".pfx",
        ".sqlite",
        ".sqlite3",
    }
    for raw_path in paths:
        path = Path(raw_path)
        normalized = path.as_posix()
        basename = path.name
        is_env = (
            basename == ".env"
            or (
                basename.startswith(".env.")
                and not basename.endswith(".example")
            )
            or basename == ".traefik-dns.env"
        )
        if (
            is_env
            or "/.secrets/" in f"/{normalized}/"
            or normalized.startswith("storage/")
            or path.suffix.lower() in secret_suffixes
        ):
            unsafe.append(normalized)
    return sorted(set(unsafe))


def _service_network_names(service: dict[str, Any]) -> set[str]:
    networks = service.get("networks") or {}
    if isinstance(networks, list):
        return {str(network) for network in networks}
    if isinstance(networks, dict):
        return {str(network) for network in networks}
    return set()


def _has_loopback_port(ports: Any, target: int) -> bool:
    for port in ports if isinstance(ports, list) else []:
        if isinstance(port, dict):
            if (
                int(port.get("published") or 0) == target
                and port.get("host_ip") == "127.0.0.1"
            ):
                return True
        elif isinstance(port, str):
            parts = port.split(":")
            if len(parts) >= 3 and parts[0] == "127.0.0.1":
                try:
                    if int(parts[-2]) == target:
                        return True
                except ValueError:
                    continue
    return False


def _has_read_only_docker_socket(service: dict[str, Any]) -> bool:
    for volume in service.get("volumes") or []:
        if isinstance(volume, dict):
            source = str(volume.get("source") or "")
            target = str(volume.get("target") or "")
            if (
                source.endswith("/docker.sock")
                and target.endswith("/docker.sock")
                and volume.get("read_only") is True
            ):
                return True
        elif isinstance(volume, str):
            if "/docker.sock:/var/run/docker.sock:ro" in volume:
                return True
    return False


def _metadata_errors(
    path: Path,
    label: str,
    expected_uid: int,
    expected_mode: int,
) -> list[str]:
    """Validate host ownership and exact POSIX mode for one existing path."""
    metadata = path.stat()
    errors = []
    actual_mode = metadata.st_mode & 0o777
    if actual_mode != expected_mode:
        errors.append(
            f"{label} permissions must be {expected_mode:04o} "
            f"(found {actual_mode:04o})"
        )
    actual_uid = getattr(metadata, "st_uid", expected_uid)
    if actual_uid != expected_uid:
        errors.append(
            f"{label} owner UID must be {expected_uid} "
            f"(found {actual_uid})"
        )
    return errors


class DoctorRunner:
    """Collect P-BitM preflight results without modifying project state."""

    def __init__(self, config, project_root: Path | None = None):
        self.config = config
        self.project_root = (
            Path(project_root).resolve()
            if project_root
            else Path(__file__).resolve().parent.parent
        )
        self.checks: list[DoctorCheck] = []
        self.docker_client = None
        self.compose_command: list[str] | None = None
        self.compose_config: dict[str, Any] | None = None

    def run(self, strict: bool = False) -> DoctorReport:
        """Run every check and return a deterministic report."""
        groups = (
            ("Configuration", self._check_configuration),
            ("Runtime profile", self._check_release_profile),
            ("Project files", self._check_project_files),
            ("Runtime environment", self._check_runtime_environment),
            ("DNS challenge", self._check_dns_secrets),
            ("Storage", self._check_storage),
            ("Database integrity", self._check_database),
            ("Local TLS", self._check_tls),
            ("Host tools", self._check_host_tools),
            ("Tracked runtime data", self._check_tracked_secrets),
            ("Docker daemon", self._check_docker),
            ("Compose configuration", self._check_compose),
            ("Required images", self._check_images),
        )
        for name, check in groups:
            first_result = len(self.checks)
            try:
                check()
            except Exception as exc:
                del self.checks[first_result:]
                self.add(
                    name,
                    CheckStatus.FAIL,
                    f"check could not complete: {type(exc).__name__}: {exc}",
                    "Correct the reported state and rerun doctor.",
                )
        return DoctorReport(tuple(self.checks), strict=strict)

    def add(
        self,
        name: str,
        status: CheckStatus,
        detail: str,
        action: str = "",
    ) -> None:
        self.checks.append(
            DoctorCheck(
                name,
                status,
                detail,
                action if status in {CheckStatus.WARN, CheckStatus.FAIL} else "",
            )
        )

    def path(self, configured: str | Path) -> Path:
        candidate = Path(configured)
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        return candidate.absolute()

    @property
    def expected_owner_uid(self) -> int:
        """Use the checkout owner even when doctor was invoked through sudo."""
        metadata = self.project_root.stat()
        fallback_uid = getattr(os, "geteuid", lambda: -1)()
        return getattr(metadata, "st_uid", fallback_uid)

    def _check_configuration(self) -> None:
        path = Path(self.config.config_path)
        if not path.exists():
            self.add(
                "Configuration",
                CheckStatus.FAIL,
                f"missing {path}",
                "Restore config.yaml before running setup.",
            )
            return
        try:
            values = yaml.safe_load(path.read_text()) or {}
        except (OSError, yaml.YAMLError) as exc:
            self.add(
                "Configuration",
                CheckStatus.FAIL,
                f"cannot parse {path.name}: {exc}",
                "Fix the YAML syntax.",
            )
            return

        errors = validate_configuration(values)
        if errors:
            self.add(
                "Configuration",
                CheckStatus.FAIL,
                "; ".join(errors),
                "Correct config.yaml and rerun doctor.",
            )
            return
        self.add(
            "Configuration",
            CheckStatus.PASS,
            f"{path.name} is valid",
        )

        configured_version = str(values["app"]["version"])
        self.add(
            "Version consistency",
            (
                CheckStatus.PASS
                if configured_version == __version__
                else CheckStatus.FAIL
            ),
            f"config {configured_version}, CLI {__version__}",
            "Keep config.yaml and cli/__init__.py versions aligned.",
        )

    def _check_release_profile(self) -> None:
        environment = self.config.get("app.environment", "")
        if environment == "production":
            self.add(
                "Runtime profile",
                CheckStatus.PASS,
                "production",
            )
        elif environment == "development":
            self.add(
                "Runtime profile",
                CheckStatus.WARN,
                "development",
                "Use app.environment=production for a release deployment.",
            )
        else:
            self.add(
                "Runtime profile",
                CheckStatus.FAIL,
                f"invalid profile: {environment or 'empty'}",
                "Set app.environment to development or production.",
            )

    def _check_project_files(self) -> None:
        required = {
            self.path(
                self.config.get(
                    "paths.docker_compose_dev"
                    if self.config.get("app.environment") == "development"
                    else "paths.docker_compose",
                    "./server/docker-compose.yml",
                )
            ),
            self.project_root / "server" / "frontend" / "Dockerfile",
            self.project_root / "server" / "backend" / "Dockerfile",
            self.project_root / "modules",
        }
        architecture = _architecture()
        for image in (self.config.get("docker.images", {}) or {}).values():
            if not isinstance(image, dict) or not image.get("enabled", True):
                continue
            context = image.get("context")
            if context:
                required.add(self.path(context))
            dockerfile = image.get(f"dockerfile_{architecture}") or image.get(
                "dockerfile"
            )
            if dockerfile:
                required.add(self.path(dockerfile))

        if self.config.get("app.environment") == "production":
            required.add(
                self.path(
                    self.config.get(
                        "paths.traefik_prod_template",
                        "./server/traefik/traefik.prod.template.yml",
                    )
                )
            )

        missing = sorted(
            _relative(path, self.project_root)
            for path in required
            if not path.exists()
        )
        self.add(
            "Project files",
            CheckStatus.FAIL if missing else CheckStatus.PASS,
            (
                f"missing: {', '.join(missing)}"
                if missing
                else f"{len(required)} required path(s) found"
            ),
            "Restore missing source files or correct their configured paths.",
        )

    def _check_runtime_environment(self) -> None:
        path = self.path(
            self.config.get("paths.env_file", "./server/.env")
        )
        if not path.is_file() or path.is_symlink():
            self.add(
                "Runtime environment",
                CheckStatus.FAIL,
                f"missing or invalid {_relative(path, self.project_root)}",
                "Run `python3 p-bitm.py setup`.",
            )
            return

        values = read_env_file(path)
        errors = get_runtime_env_errors(values)
        errors.extend(
            _metadata_errors(
                path,
                _relative(path, self.project_root),
                self.expected_owner_uid,
                0o600,
            )
        )
        if values.get("ENVIRONMENT") != self.config.get("app.environment"):
            errors.append("ENVIRONMENT does not match config.yaml")
        try:
            ipaddress.ip_address(values.get("IP", ""))
        except ValueError:
            errors.append("IP is not a valid address")

        expected_storage = self.path(
            self.config.get("paths.storage_dir", "./storage")
        )
        configured_storage = values.get("HOST_STORAGE_PATH", "")
        if configured_storage:
            try:
                if Path(configured_storage).resolve() != expected_storage:
                    errors.append("HOST_STORAGE_PATH does not match storage_dir")
            except OSError:
                errors.append("HOST_STORAGE_PATH is invalid")

        self.add(
            "Runtime environment",
            CheckStatus.FAIL if errors else CheckStatus.PASS,
            "; ".join(errors) if errors else "valid, permissions 0600",
            "Run setup to reconcile generated runtime values.",
        )

    def _check_dns_secrets(self) -> None:
        if self.config.get("app.environment") != "production":
            self.add(
                "DNS challenge",
                CheckStatus.SKIP,
                "not required in development",
            )
            return

        provider = str(
            self.config.get("ssl.dns_challenge.provider", "")
        )
        credentials = self.config.get(
            "ssl.dns_challenge.credentials",
            [],
        )
        directory = self.path(
            self.config.get(
                "paths.dns_secrets_dir",
                "./server/.secrets/dns",
            )
        )
        errors = []
        if (
            not directory.is_dir()
            or directory.is_symlink()
        ):
            errors.append("secret directory must exist with permissions 0700")
        else:
            errors.extend(
                _metadata_errors(
                    directory,
                    _relative(directory, self.project_root),
                    self.expected_owner_uid,
                    0o700,
                )
            )

        for variable in credentials if isinstance(credentials, list) else []:
            secret = directory / str(variable)
            try:
                if (
                    not secret.is_file()
                    or secret.is_symlink()
                    or not secret.read_text().strip()
                ):
                    errors.append(f"{variable} is missing, empty, or not 0600")
                else:
                    errors.extend(
                        _metadata_errors(
                            secret,
                            variable,
                            self.expected_owner_uid,
                            0o600,
                        )
                    )
            except OSError:
                errors.append(f"{variable} cannot be read")

        dns_env = self.path(
            self.config.get(
                "paths.traefik_dns_env_file",
                "./server/.traefik-dns.env",
            )
        )
        runtime = self.path(
            self.config.get(
                "paths.traefik_prod_runtime",
                "./server/traefik/traefik.prod.runtime.yml",
            )
        )
        env_values = read_env_file(dns_env)
        if (
            not dns_env.is_file()
            or dns_env.is_symlink()
        ):
            errors.append("Traefik DNS environment is missing or not 0600")
        else:
            errors.extend(
                _metadata_errors(
                    dns_env,
                    _relative(dns_env, self.project_root),
                    self.expected_owner_uid,
                    0o600,
                )
            )
            for variable in credentials:
                expected = f"/run/secrets/dns/{variable}"
                if env_values.get(f"{variable}_FILE") != expected:
                    errors.append(f"{variable}_FILE mapping is invalid")
                if variable in env_values:
                    errors.append(f"{variable} must not be stored in the env file")
        if not runtime.is_file() or runtime.is_symlink():
            errors.append("generated Traefik runtime config is missing")
        else:
            errors.extend(
                _metadata_errors(
                    runtime,
                    _relative(runtime, self.project_root),
                    self.expected_owner_uid,
                    0o644,
                )
            )

        self.add(
            f"DNS challenge ({provider or 'unset'})",
            CheckStatus.FAIL if errors else CheckStatus.PASS,
            (
                "; ".join(errors)
                if errors
                else f"{len(credentials)} credential file(s) ready"
            ),
            "Run setup to provision DNS credentials and runtime files.",
        )

    def _check_storage(self) -> None:
        configured = [
            self.path(self.config.get("paths.storage_dir", "./storage")),
            self.path(
                self.config.get(
                    "paths.campaigns_dir",
                    "./storage/campaigns",
                )
            ),
        ]
        errors = []
        for path in configured:
            label = _relative(path, self.project_root)
            if not path.is_dir() or path.is_symlink():
                errors.append(f"{label} is missing")
            else:
                errors.extend(
                    _metadata_errors(
                        path,
                        label,
                        self.expected_owner_uid,
                        0o755,
                    )
                )
            if path.is_dir() and not path.is_symlink() and not os.access(
                path,
                os.R_OK | os.W_OK | os.X_OK,
            ):
                errors.append(f"{label} is not accessible")

        if errors:
            self.add(
                "Storage",
                CheckStatus.FAIL,
                "; ".join(errors),
                "Run setup and correct host directory ownership.",
            )
            return

        free_bytes = shutil.disk_usage(configured[0]).free
        if free_bytes < CRITICAL_FREE_STORAGE_BYTES:
            status = CheckStatus.FAIL
            action = "Free at least 1 GiB before starting an engagement."
        elif free_bytes < MIN_FREE_STORAGE_BYTES:
            status = CheckStatus.WARN
            action = "Free at least 5 GiB before a long engagement."
        else:
            status = CheckStatus.PASS
            action = ""
        self.add(
            "Storage",
            status,
            f"{_format_bytes(free_bytes)} free, configured directories writable",
            action,
        )

    def _check_database(self) -> None:
        path = self.path(
            self.config.get(
                "database.path",
                self.config.get("paths.database", "./storage/p-bitm.db"),
            )
        )
        if not path.exists():
            self.add(
                "Database integrity",
                CheckStatus.SKIP,
                "database will be created on first backend start",
            )
            return
        if not path.is_file() or path.is_symlink():
            self.add(
                "Database integrity",
                CheckStatus.FAIL,
                "configured database is not a regular file",
                "Restore a valid SQLite database.",
            )
            return
        metadata_errors = _metadata_errors(
            path,
            _relative(path, self.project_root),
            self.expected_owner_uid,
            0o644,
        )
        if metadata_errors:
            self.add(
                "Database integrity",
                CheckStatus.FAIL,
                "; ".join(metadata_errors),
                "Correct the database ownership and permissions on the host.",
            )
            return
        try:
            connection = sqlite3.connect(
                f"{path.as_uri()}?mode=ro&immutable=1",
                uri=True,
                timeout=2,
            )
            try:
                result = connection.execute("PRAGMA quick_check").fetchone()
            finally:
                connection.close()
            healthy = bool(result and result[0] == "ok")
            self.add(
                "Database integrity",
                CheckStatus.PASS if healthy else CheckStatus.FAIL,
                "SQLite quick_check: ok" if healthy else f"SQLite: {result}",
                "Restore the database from a known-good backup.",
            )
        except (OSError, sqlite3.Error) as exc:
            self.add(
                "Database integrity",
                CheckStatus.FAIL,
                f"read-only check failed: {exc}",
                "Verify database ownership and integrity.",
            )

    def _check_tls(self) -> None:
        directory = self.path(
            self.config.get("paths.certs_dir", "./certs")
        )
        certificate = directory / "cert.pem"
        private_key = directory / "key.pem"
        errors = []
        warnings = []
        if not certificate.is_file() or certificate.is_symlink():
            errors.append("cert.pem is missing or invalid")
        else:
            errors.extend(
                _metadata_errors(
                    certificate,
                    _relative(certificate, self.project_root),
                    self.expected_owner_uid,
                    0o644,
                )
            )
        if not private_key.is_file() or private_key.is_symlink():
            errors.append("key.pem is missing or invalid")
        else:
            errors.extend(
                _metadata_errors(
                    private_key,
                    _relative(private_key, self.project_root),
                    self.expected_owner_uid,
                    0o600,
                )
            )

        if not errors:
            try:
                decoded = ssl._ssl._test_decode_cert(str(certificate))
                expires = datetime.strptime(
                    decoded["notAfter"],
                    "%b %d %H:%M:%S %Y %Z",
                ).replace(tzinfo=timezone.utc)
                remaining = (expires - datetime.now(timezone.utc)).days
                if remaining < 0:
                    errors.append("certificate has expired")
                elif remaining < MIN_CERTIFICATE_DAYS:
                    warnings.append(f"certificate expires in {remaining} day(s)")
            except (KeyError, OSError, ValueError, ssl.SSLError) as exc:
                errors.append(f"cannot decode cert.pem: {exc}")

        if not errors and shutil.which("openssl"):
            certificate_key = _run_text(
                [
                    "openssl",
                    "x509",
                    "-in",
                    str(certificate),
                    "-pubkey",
                    "-noout",
                ]
            )
            private_public = _run_text(
                [
                    "openssl",
                    "pkey",
                    "-in",
                    str(private_key),
                    "-pubout",
                ]
            )
            if certificate_key is None or private_public is None:
                errors.append("OpenSSL could not inspect the certificate pair")
            elif certificate_key.strip() != private_public.strip():
                errors.append("certificate and private key do not match")

        if errors:
            status = CheckStatus.FAIL
            detail = "; ".join(errors)
        elif warnings:
            status = CheckStatus.WARN
            detail = "; ".join(warnings)
        else:
            status = CheckStatus.PASS
            detail = "certificate and private key are valid"
        self.add(
            "Local TLS",
            status,
            detail,
            "Run setup to reconcile or regenerate the local certificate pair.",
        )

    def _check_host_tools(self) -> None:
        minimum_python = (3, 9)
        python_ready = sys.version_info >= minimum_python
        self.add(
            "Python runtime",
            CheckStatus.PASS if python_ready else CheckStatus.FAIL,
            platform.python_version(),
            "Install Python 3.9 or newer for the host CLI.",
        )

        tools = {
            "docker": shutil.which("docker"),
            "git": shutil.which("git"),
            "openssl": shutil.which("openssl"),
        }
        missing = sorted(name for name, path in tools.items() if not path)
        self.add(
            "Host tools",
            CheckStatus.FAIL if missing else CheckStatus.PASS,
            (
                f"missing: {', '.join(missing)}"
                if missing
                else "docker, git, openssl"
            ),
            "Install the missing command-line tools.",
        )

        buildx_version = get_docker_buildx_version()
        self.add(
            "Docker Buildx",
            CheckStatus.PASS if buildx_version else CheckStatus.FAIL,
            buildx_version or "not available",
            (
                "Install the Buildx plugin package provided by your Docker "
                "distribution."
            ),
        )

        buildkit_disabled = docker_buildkit_is_disabled()
        self.add(
            "BuildKit configuration",
            CheckStatus.FAIL if buildkit_disabled else CheckStatus.PASS,
            (
                "disabled by DOCKER_BUILDKIT=0"
                if buildkit_disabled
                else "enabled by default"
            ),
            "Unset DOCKER_BUILDKIT instead of forcing the legacy builder.",
        )

        compose_version = get_docker_compose_version()
        self.compose_command = (
            ["docker", "compose"] if compose_version else None
        )
        self.add(
            "Docker Compose plugin",
            (
                CheckStatus.PASS
                if self.compose_command
                else CheckStatus.FAIL
            ),
            compose_version or "not available",
            (
                "Install the Compose v2 plugin package provided by your "
                "Docker distribution; standalone `docker-compose` is not "
                "supported."
            ),
        )

    def _check_tracked_secrets(self) -> None:
        result = _run_text(
            ["git", "-C", str(self.project_root), "ls-files"]
        )
        if result is None:
            self.add(
                "Tracked runtime data",
                CheckStatus.WARN,
                "Git index could not be inspected",
                "Run `git ls-files` and review generated files manually.",
            )
            return
        unsafe = find_tracked_secret_paths(result.splitlines())
        self.add(
            "Tracked runtime data",
            CheckStatus.FAIL if unsafe else CheckStatus.PASS,
            (
                f"tracked generated or sensitive path(s): {', '.join(unsafe)}"
                if unsafe
                else "no generated secret or runtime data is tracked"
            ),
            "Remove generated paths from Git and rotate any exposed secrets.",
        )

    def _check_docker(self) -> None:
        try:
            self.docker_client = docker.from_env()
            version = self.docker_client.version().get("Version", "unknown")
        except Exception as exc:
            self.docker_client = None
            self.add(
                "Docker daemon",
                CheckStatus.FAIL,
                f"unavailable: {exc}",
                "Start Docker and verify access to its socket.",
            )
            return
        supported = docker_engine_is_supported(version)
        minimum = ".".join(
            str(part) for part in MIN_DOCKER_ENGINE_VERSION
        )
        self.add(
            "Docker daemon",
            CheckStatus.PASS if supported else CheckStatus.FAIL,
            f"version {version}",
            f"Upgrade Docker Engine to version {minimum} or newer.",
        )

    def _check_compose(self) -> None:
        if not self.compose_command:
            self.add(
                "Compose configuration",
                CheckStatus.SKIP,
                "Docker Compose is unavailable",
            )
            self.add(
                "Network topology",
                CheckStatus.SKIP,
                "Compose configuration was not evaluated",
            )
            return

        compose_path = self.path(
            self.config.get(
                "paths.docker_compose_dev"
                if self.config.get("app.environment") == "development"
                else "paths.docker_compose",
                "./server/docker-compose.yml",
            )
        )
        command = self.compose_command + [
            "-f",
            str(compose_path),
            "config",
            "--format",
            "json",
        ]
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.add(
                "Compose configuration",
                CheckStatus.FAIL,
                f"validation failed: {exc}",
                "Fix Docker Compose installation or project configuration.",
            )
            self.add(
                "Network topology",
                CheckStatus.SKIP,
                "Compose configuration was not evaluated",
            )
            return

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            self.add(
                "Compose configuration",
                CheckStatus.FAIL,
                detail[:1_000] or "invalid",
                "Correct the Compose file and generated environment files.",
            )
            self.add(
                "Network topology",
                CheckStatus.SKIP,
                "Compose configuration is invalid",
            )
            return

        try:
            self.compose_config = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.add(
                "Compose configuration",
                CheckStatus.FAIL,
                f"invalid JSON output: {exc}",
                "Upgrade Docker Compose to a version supporting JSON config.",
            )
            self.add(
                "Network topology",
                CheckStatus.SKIP,
                "Compose output could not be parsed",
            )
            return

        self.add(
            "Compose configuration",
            CheckStatus.PASS,
            f"{compose_path.name} is valid",
        )
        errors = validate_network_topology(self.compose_config)
        self.add(
            "Network topology",
            CheckStatus.FAIL if errors else CheckStatus.PASS,
            "; ".join(errors) if errors else "one-host isolation boundaries are valid",
            "Restore the expected dashboard, campaign, and socket-proxy networks.",
        )

    def _check_images(self) -> None:
        if self.docker_client is None:
            self.add(
                "Required images",
                CheckStatus.SKIP,
                "Docker daemon is unavailable",
            )
            self.add(
                "Image freshness",
                CheckStatus.SKIP,
                "Docker daemon is unavailable",
            )
            return

        configured_images = []
        for image in (self.config.get("docker.images", {}) or {}).values():
            if (
                isinstance(image, dict)
                and image.get("enabled", True)
                and image.get("name")
            ):
                configured_images.append(
                    (str(image["name"]), image.get("context"))
                )
        configured_images.extend(
            (
                str(name),
                _compose_build_context(self.compose_config, str(name)),
            )
            for name in self.config.get("docker.compose_images", []) or []
        )

        missing = []
        stale = []
        for name, context in configured_images:
            try:
                image = self.docker_client.images.get(name)
            except docker.errors.ImageNotFound:
                missing.append(name)
                continue
            except Exception:
                missing.append(name)
                continue

            if context:
                source_root = self.path(context)
                latest_source = _latest_source_mtime(source_root)
                created = _parse_docker_timestamp(
                    image.attrs.get("Created")
                )
                if (
                    latest_source is not None
                    and created is not None
                    and latest_source > created.timestamp()
                ):
                    stale.append(name)

        self.add(
            "Required images",
            CheckStatus.FAIL if missing else CheckStatus.PASS,
            (
                f"missing: {', '.join(sorted(missing))}"
                if missing
                else f"{len(configured_images)} application image(s) available"
            ),
            "Run `python3 p-bitm.py up --build` before release.",
        )
        self.add(
            "Image freshness",
            CheckStatus.PASS,
            (
                "non-blocking source timestamp drift for: "
                f"{', '.join(sorted(stale))}; BuildKit may have reused "
                "content-addressed layers"
                if stale
                else "configured custom images match source timestamps"
            ),
            (
                "Run `python3 p-bitm.py up --build` when source content has "
                "changed; timestamps alone cannot prove cache staleness."
                if stale
                else ""
            ),
        )


def _architecture() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in {"aarch64", "arm64"} else "amd64"


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _format_bytes(value: int) -> str:
    return f"{value / 1024**3:.1f} GiB"


def _run_text(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _parse_docker_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    match = re.match(
        r"^(?P<prefix>.+\.)(?P<fraction>\d+)(?P<offset>[+-]\d\d:\d\d)$",
        normalized,
    )
    if match and len(match.group("fraction")) > 6:
        normalized = (
            f"{match.group('prefix')}{match.group('fraction')[:6]}"
            f"{match.group('offset')}"
        )
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _compose_build_context(
    compose: dict[str, Any] | None,
    image_name: str,
) -> str | None:
    if not isinstance(compose, dict):
        return None
    services = compose.get("services")
    if not isinstance(services, dict):
        return None
    service_name = image_name.rsplit("-", 1)[-1].split(":", 1)[0]
    service = services.get(service_name)
    if not isinstance(service, dict):
        return None
    build = service.get("build")
    if isinstance(build, str):
        return build
    if isinstance(build, dict) and build.get("context"):
        return str(build["context"])
    return None


def _latest_source_mtime(root: Path) -> float | None:
    if not root.exists():
        return None
    latest = root.stat().st_mtime
    candidates = [root] if root.is_file() else root.rglob("*")
    for path in candidates:
        if any(part in SOURCE_EXCLUDES for part in path.parts):
            continue
        try:
            if path.is_file() and not path.is_symlink():
                latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest
