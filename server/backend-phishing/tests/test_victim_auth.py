import unittest

from core.victim_auth import (
    derive_selkies_master_token,
    derive_victim_api_key,
)


class VictimAuthTests(unittest.TestCase):
    def test_derivation_is_deterministic(self):
        first = derive_victim_api_key("campaign-key", "victim-a")
        second = derive_victim_api_key("campaign-key", "victim-a")
        self.assertEqual(first, second)

    def test_credentials_are_scoped_to_victim(self):
        first = derive_victim_api_key("campaign-key", "victim-a")
        second = derive_victim_api_key("campaign-key", "victim-b")
        self.assertNotEqual(first, second)

    def test_credentials_are_scoped_to_campaign(self):
        first = derive_victim_api_key("campaign-a", "victim-a")
        second = derive_victim_api_key("campaign-b", "victim-a")
        self.assertNotEqual(first, second)

    def test_missing_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            derive_victim_api_key("", "victim-a")
        with self.assertRaises(ValueError):
            derive_victim_api_key("campaign-key", "")

    def test_selkies_control_token_is_separate_from_collector_key(self):
        self.assertNotEqual(
            derive_selkies_master_token("campaign-key", "victim-a"),
            derive_victim_api_key("campaign-key", "victim-a"),
        )


if __name__ == "__main__":
    unittest.main()
