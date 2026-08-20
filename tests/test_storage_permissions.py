import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from cli.utils import (
    STORAGE_DIRECTORY_MODE,
    StorageOwnershipError,
    ensure_storage_directories,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StorageDirectoryTests(unittest.TestCase):
    def _config_value(self, storage: Path, campaigns: Path):
        values = {
            "paths.storage_dir": str(storage),
            "paths.campaigns_dir": str(campaigns),
        }
        return lambda key, default=None: values.get(key, default)

    def test_creates_private_storage_for_the_current_user(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage = Path(temporary_directory) / "storage"
            campaigns = storage / "campaigns"
            config_values = self._config_value(storage, campaigns)
            project_metadata = PROJECT_ROOT.stat()
            with patch(
                "cli.utils.config.get",
                side_effect=config_values,
            ), patch(
                "cli.utils.os.geteuid",
                return_value=project_metadata.st_uid,
            ), patch(
                "cli.utils.os.getegid",
                return_value=project_metadata.st_gid,
            ), patch(
                "cli.utils.platform.system",
                return_value="Darwin",
            ):
                resolved_storage, resolved_campaigns = ensure_storage_directories()

            self.assertEqual(resolved_storage, storage.resolve())
            self.assertEqual(resolved_campaigns, campaigns.resolve())
            self.assertEqual(
                storage.stat().st_mode & 0o777,
                STORAGE_DIRECTORY_MODE,
            )
            self.assertEqual(
                campaigns.stat().st_mode & 0o777,
                STORAGE_DIRECTORY_MODE,
            )

    def test_refuses_to_prepare_storage_as_root(self):
        with patch("cli.utils.os.geteuid", return_value=0):
            with self.assertRaisesRegex(StorageOwnershipError, "without sudo"):
                ensure_storage_directories()


class ComposeStorageTests(unittest.TestCase):
    def test_compose_does_not_create_missing_host_storage(self):
        for compose_path in (
            PROJECT_ROOT / "server/docker-compose.yml",
            PROJECT_ROOT / "server/docker-compose-dev.yml",
        ):
            with self.subTest(compose=compose_path.name):
                compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
                volumes = compose["services"]["backend"]["volumes"]
                storage_mount = next(
                    volume
                    for volume in volumes
                    if volume.get("target") == "/storage"
                )
                self.assertEqual(storage_mount.get("type"), "bind")
                self.assertEqual(storage_mount.get("source"), "../storage")
                self.assertFalse(
                    storage_mount.get("bind", {}).get("create_host_path")
                )


if __name__ == "__main__":
    unittest.main()
