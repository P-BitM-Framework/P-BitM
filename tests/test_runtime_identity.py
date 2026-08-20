import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cli.runtime_identity import (
    RuntimeIdentity,
    RuntimeIdentityError,
    resolve_runtime_identity,
)
from cli.runtime_env import get_runtime_env_errors


class RuntimeIdentityTests(unittest.TestCase):
    def test_uses_current_linux_user(self):
        identity = resolve_runtime_identity(
            system_name="Linux",
            effective_uid=1001,
            effective_gid=1002,
            environment={},
        )

        self.assertEqual(identity, RuntimeIdentity(1001, 1002, "current-user"))

    def test_uses_original_user_when_invoked_through_sudo(self):
        identity = resolve_runtime_identity(
            system_name="Linux",
            effective_uid=0,
            effective_gid=0,
            environment={"SUDO_UID": "1007", "SUDO_GID": "1008"},
        )

        self.assertEqual(identity, RuntimeIdentity(1007, 1008, "sudo-user"))

    def test_direct_root_uses_non_root_repository_owner(self):
        with patch(
            "cli.runtime_identity.Path.stat",
            return_value=SimpleNamespace(st_uid=1200, st_gid=1300),
        ):
            identity = resolve_runtime_identity(
                Path("/project"),
                system_name="Linux",
                effective_uid=0,
                effective_gid=0,
                environment={},
            )

        self.assertEqual(
            identity,
            RuntimeIdentity(1200, 1300, "repository-owner"),
        )

    def test_direct_root_never_selects_uid_zero(self):
        with patch(
            "cli.runtime_identity.Path.stat",
            return_value=SimpleNamespace(st_uid=0, st_gid=0),
        ):
            identity = resolve_runtime_identity(
                Path("/project"),
                system_name="Linux",
                effective_uid=0,
                effective_gid=0,
                environment={},
            )

        self.assertEqual(identity, RuntimeIdentity(1000, 1000, "root-default"))

    def test_non_linux_hosts_keep_the_container_default(self):
        identity = resolve_runtime_identity(
            system_name="Darwin",
            effective_uid=501,
            effective_gid=20,
            environment={},
        )

        self.assertEqual(
            identity,
            RuntimeIdentity(1000, 1000, "container-default"),
        )

    def test_rejects_partial_sudo_identity(self):
        with self.assertRaisesRegex(RuntimeIdentityError, "both be set"):
            resolve_runtime_identity(
                system_name="Linux",
                effective_uid=0,
                effective_gid=0,
                environment={"SUDO_UID": "1000"},
            )

    def test_runtime_environment_rejects_root_ids(self):
        values = {
            "ENVIRONMENT": "development",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "a" * 32,
            "INTERNAL_API_KEY": "i" * 32,
            "DATA_ENCRYPTION_KEY": "e" * 32,
            "HOST_STORAGE_PATH": "/storage",
            "IP": "127.0.0.1",
            "PBITM_UID": "0",
            "PBITM_GID": "1000",
        }

        self.assertIn("invalid PBITM_UID", get_runtime_env_errors(values))


if __name__ == "__main__":
    unittest.main()
