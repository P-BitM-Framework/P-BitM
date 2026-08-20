import os
import unittest
from unittest.mock import patch

from utils.runtime_identity import runtime_identity_environment


class RuntimeIdentityEnvironmentTests(unittest.TestCase):
    def test_passes_selected_ids_to_linuxserver_images(self):
        with patch.dict(
            os.environ,
            {"PBITM_UID": "1001", "PBITM_GID": "1002"},
            clear=False,
        ):
            environment = runtime_identity_environment(linuxserver=True)

        self.assertEqual(
            environment,
            {
                "PBITM_UID": "1001",
                "PBITM_GID": "1002",
                "PUID": "1001",
                "PGID": "1002",
            },
        )

    def test_rejects_root_container_identity(self):
        with patch.dict(
            os.environ,
            {"PBITM_UID": "0", "PBITM_GID": "1000"},
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "between 1"):
                runtime_identity_environment()


if __name__ == "__main__":
    unittest.main()
