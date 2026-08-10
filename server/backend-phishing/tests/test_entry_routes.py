import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


TEST_ENV = {
    "CAMPAIGN_ID": "49d28a23",
    "CAMPAIGN_PROTOCOL": "vnc",
    "ENVIRONMENT": "production",
    "INTERNAL_API_KEY": "campaign-internal-key",
    "GATEWAY_AUTH_KEY": "gateway-auth-key",
    "SESSION_TOKEN_SECRET": "session-token-secret",
    "ENTRY_PATH": "auth/callback",
    "TRACKING_PARAMETER": "",
    "DB_PATH": "/tmp/pbitm-entry-test.db",
}

with patch.dict(os.environ, TEST_ENV):
    from config import settings  # noqa: E402
    from routes.tracking import tracking_router  # noqa: E402


class PublicEntryRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(tracking_router)
        cls.client = TestClient(app)

    def setUp(self):
        settings_patch = patch.multiple(
            settings,
            CAMPAIGN_ID="49d28a23",
            ENVIRONMENT="production",
            ENTRY_PATH="auth/callback",
            TRACKING_PARAMETER="",
        )
        settings_patch.start()
        self.addCleanup(settings_patch.stop)

    @patch(
        "routes.tracking.queue_tracking_event",
        new_callable=AsyncMock,
    )
    @patch("routes.tracking.get_victim_by_tracking_id")
    def test_path_capability_redirects_to_clean_target_path(
        self,
        get_victim,
        _track_event,
    ):
        get_victim.return_value = {"id": "deadbeef"}

        response = self.client.get(
            "/auth/callback/opaque-token",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/auth/callback")
        self.assertNotIn("opaque-token", response.headers["set-cookie"])

    @patch(
        "routes.tracking.queue_tracking_event",
        new_callable=AsyncMock,
    )
    @patch("routes.tracking.get_victim_by_tracking_id")
    def test_optional_query_capability_uses_the_same_clean_redirect(
        self,
        get_victim,
        _track_event,
    ):
        get_victim.return_value = {"id": "deadbeef"}
        settings.TRACKING_PARAMETER = "state"

        response = self.client.get(
            "/auth/callback?state=opaque-token",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/auth/callback")
        self.assertNotIn("opaque-token", response.headers["set-cookie"])

    @patch(
        "routes.tracking.queue_tracking_event",
        new_callable=AsyncMock,
    )
    @patch("routes.tracking.get_victim_by_tracking_id")
    def test_development_redirect_keeps_campaign_prefix(
        self,
        get_victim,
        _track_event,
    ):
        get_victim.return_value = {"id": "deadbeef"}
        settings.ENVIRONMENT = "development"

        response = self.client.get(
            "/auth/callback/opaque-token",
            follow_redirects=False,
        )

        self.assertEqual(
            response.headers["location"],
            "/49d28a23/auth/callback",
        )


if __name__ == "__main__":
    unittest.main()
