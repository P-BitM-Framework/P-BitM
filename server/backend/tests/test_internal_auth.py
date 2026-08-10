import unittest

from utils.internal_auth import (
    derive_campaign_api_key,
    derive_selkies_master_token,
    derive_victim_api_key,
)


class CampaignInternalAuthTests(unittest.TestCase):
    def test_derivation_is_deterministic(self):
        first = derive_campaign_api_key("master-secret", "campaign-a")
        second = derive_campaign_api_key("master-secret", "campaign-a")
        self.assertEqual(first, second)

    def test_campaigns_receive_different_credentials(self):
        first = derive_campaign_api_key("master-secret", "campaign-a")
        second = derive_campaign_api_key("master-secret", "campaign-b")
        self.assertNotEqual(first, second)

    def test_different_master_keys_produce_different_credentials(self):
        first = derive_campaign_api_key("master-secret-a", "campaign-a")
        second = derive_campaign_api_key("master-secret-b", "campaign-a")
        self.assertNotEqual(first, second)

    def test_missing_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            derive_campaign_api_key("", "campaign-a")
        with self.assertRaises(ValueError):
            derive_campaign_api_key("master-secret", "")

    def test_victim_credentials_are_scoped(self):
        campaign_key = derive_campaign_api_key("master-secret", "campaign-a")
        first = derive_victim_api_key(campaign_key, "victim-a")
        second = derive_victim_api_key(campaign_key, "victim-b")
        self.assertNotEqual(first, second)

    def test_selkies_control_token_uses_a_separate_context(self):
        campaign_key = derive_campaign_api_key("master-secret", "campaign-a")
        self.assertNotEqual(
            derive_selkies_master_token(campaign_key, "victim-a"),
            derive_victim_api_key(campaign_key, "victim-a"),
        )


if __name__ == "__main__":
    unittest.main()
