import unittest

from utils.public_routes import build_public_access_url, derive_entry_path


class PublicEntryPathTests(unittest.TestCase):
    def test_preserves_target_path(self):
        self.assertEqual(
            derive_entry_path("https://example.com/account/signin?next=/home"),
            "account/signin",
        )

    def test_root_target_uses_no_synthetic_prefix(self):
        self.assertEqual(derive_entry_path("https://example.com/"), "")

    def test_normalizes_unsafe_segments(self):
        self.assertEqual(
            derive_entry_path("https://example.com/auth/%2E%2E/call back"),
            "auth/call-back",
        )


class PublicAccessURLTests(unittest.TestCase):
    def test_development_path_does_not_duplicate_campaign_prefix(self):
        self.assertEqual(
            build_public_access_url(
                "https://192.168.188.76/aea6e106/",
                "/aea6e106/OY4FK1sp/route/access/token",
            ),
            "https://192.168.188.76/aea6e106/OY4FK1sp/route/access/token",
        )

    def test_production_path_uses_domain_origin(self):
        self.assertEqual(
            build_public_access_url(
                "https://campaign.example.org/",
                "/OY4FK1sp/route/access/token",
            ),
            "https://campaign.example.org/OY4FK1sp/route/access/token",
        )

    def test_rejects_relative_access_path(self):
        with self.assertRaises(ValueError):
            build_public_access_url(
                "https://campaign.example.org/",
                "OY4FK1sp/route/access/token",
            )


if __name__ == "__main__":
    unittest.main()
