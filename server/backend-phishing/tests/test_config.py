import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from config import Settings


REQUIRED_SETTINGS = {
    "CAMPAIGN_ID": "49d28a23",
    "INTERNAL_API_KEY": "campaign-internal-key",
    "GATEWAY_AUTH_KEY": "gateway-auth-key",
    "SESSION_TOKEN_SECRET": "session-token-secret",
}


class CampaignSettingsTests(unittest.TestCase):
    def build_settings(self, **overrides):
        with patch.dict(os.environ, {}, clear=True):
            return Settings(
                _env_file=None,
                **REQUIRED_SETTINGS,
                **overrides,
            )

    def test_uses_sqlite_path_and_internal_api_defaults(self):
        settings = self.build_settings()

        self.assertEqual(settings.DB_PATH, "/storage/p-bitm.db")
        self.assertEqual(
            settings.ADMIN_API_URL,
            "http://bitm-backend:8443",
        )

    def test_accepts_legacy_admin_backend_url_alias(self):
        settings = self.build_settings(
            ADMIN_BACKEND_URL="http://legacy-admin:8443/",
        )

        self.assertEqual(
            settings.ADMIN_API_URL,
            "http://legacy-admin:8443/",
        )

    def test_rejects_non_positive_runtime_limits(self):
        for field_name in (
            "MAX_ACTIVE_SESSIONS",
            "SESSION_TOKEN_TTL_SECONDS",
            "WS_HANDSHAKE_TIMEOUT_SECONDS",
            "WS_MAX_MESSAGE_BYTES",
            "WS_MESSAGE_RATE_WINDOW_SECONDS",
            "WS_MESSAGE_RATE_MAX_MESSAGES",
            "WS_MAX_QUEUE",
            "WS_MAX_WEBRTC_CANDIDATES",
            "TRACKING_QUEUE_SIZE",
            "TRACKING_WORKERS",
            "TRACKING_RATE_LIMIT_WINDOW_SECONDS",
            "TRACKING_RATE_LIMIT_PER_CLIENT",
            "TRACKING_RATE_LIMIT_GLOBAL",
        ):
            with self.subTest(field=field_name):
                with self.assertRaises(ValidationError):
                    self.build_settings(**{field_name: 0})

    def test_rejects_unknown_environment(self):
        with self.assertRaises(ValidationError):
            self.build_settings(ENVIRONMENT="staging")


if __name__ == "__main__":
    unittest.main()
