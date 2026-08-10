import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


TEST_ENV = {
    "CAMPAIGN_ID": "49d28a23",
    "INTERNAL_API_KEY": "campaign-internal-key",
    "GATEWAY_AUTH_KEY": "gateway-auth-key",
    "SESSION_TOKEN_SECRET": "session-token-secret",
}

with patch.dict(os.environ, TEST_ENV):
    from routes.tracking import tracking_router  # noqa: E402


class TrackingPixelRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(tracking_router)
        cls.client = TestClient(app)

    @patch(
        "routes.tracking.queue_tracking_event",
        new_callable=AsyncMock,
    )
    @patch("routes.tracking.get_victim_by_tracking_id")
    def test_malformed_tracking_id_does_not_touch_database(
        self,
        get_victim,
        queue_event,
    ):
        response = self.client.get("/p/not!valid.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        get_victim.assert_not_called()
        queue_event.assert_not_awaited()

    @patch(
        "routes.tracking.queue_tracking_event",
        new_callable=AsyncMock,
    )
    @patch("routes.tracking.get_victim_by_tracking_id")
    def test_unknown_tracking_id_is_not_enqueued(
        self,
        get_victim,
        queue_event,
    ):
        get_victim.return_value = None

        response = self.client.get("/p/unknown-token.png")

        self.assertEqual(response.status_code, 200)
        get_victim.assert_called_once_with("unknown-token")
        queue_event.assert_not_awaited()

    @patch(
        "routes.tracking.queue_tracking_event",
        new_callable=AsyncMock,
    )
    @patch("routes.tracking.get_victim_by_tracking_id")
    def test_known_tracking_id_is_enqueued(
        self,
        get_victim,
        queue_event,
    ):
        get_victim.return_value = {"id": "victim"}
        queue_event.return_value = True

        response = self.client.get("/p/known-token.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["cache-control"],
            "no-store, no-cache, must-revalidate, max-age=0",
        )
        self.assertEqual(response.headers["pragma"], "no-cache")
        queue_event.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
