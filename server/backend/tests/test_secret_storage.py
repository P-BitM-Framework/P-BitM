import os
import unittest
from unittest.mock import patch

from utils.secret_storage import (
    ENCRYPTED_PREFIX,
    decrypt_secret,
    encrypt_secret,
)


class SecretStorageTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"DATA_ENCRYPTION_KEY": "e" * 32},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def test_round_trip_does_not_store_plaintext(self):
        encrypted = encrypt_secret("smtp-password")
        self.assertTrue(encrypted.startswith(ENCRYPTED_PREFIX))
        self.assertNotIn("smtp-password", encrypted)
        self.assertEqual(decrypt_secret(encrypted), "smtp-password")

    def test_encryption_is_non_deterministic(self):
        self.assertNotEqual(encrypt_secret("same"), encrypt_secret("same"))

    def test_existing_ciphertext_is_not_double_encrypted(self):
        encrypted = encrypt_secret("smtp-password")
        self.assertEqual(encrypt_secret(encrypted), encrypted)

    def test_legacy_plaintext_can_be_read_for_migration(self):
        self.assertEqual(decrypt_secret("legacy-password"), "legacy-password")

    def test_wrong_key_is_rejected(self):
        encrypted = encrypt_secret("smtp-password")
        with patch.dict(os.environ, {"DATA_ENCRYPTION_KEY": "x" * 32}):
            with self.assertRaises(RuntimeError):
                decrypt_secret(encrypted)


if __name__ == "__main__":
    unittest.main()
