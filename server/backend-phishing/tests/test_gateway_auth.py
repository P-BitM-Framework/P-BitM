import unittest

from core.gateway_auth import is_gateway_request_authorized


class GatewayAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.expected_key = "gateway-secret"
        self.active_victims = {"49d28a23"}

    def test_active_victim_with_gateway_key_is_allowed(self):
        self.assertTrue(
            is_gateway_request_authorized(
                "49d28a23",
                self.expected_key,
                self.expected_key,
                self.active_victims,
            )
        )

    def test_inactive_or_malformed_victim_is_denied(self):
        for victim_id in ("deadbeef", "../escape", "", None):
            with self.subTest(victim_id=victim_id):
                self.assertFalse(
                    is_gateway_request_authorized(
                        victim_id,
                        self.expected_key,
                        self.expected_key,
                        self.active_victims,
                    )
                )

    def test_missing_or_wrong_gateway_key_is_denied(self):
        for key in ("wrong", "", None):
            with self.subTest(key=key):
                self.assertFalse(
                    is_gateway_request_authorized(
                        "49d28a23",
                        key,
                        self.expected_key,
                        self.active_victims,
                    )
                )


if __name__ == "__main__":
    unittest.main()
