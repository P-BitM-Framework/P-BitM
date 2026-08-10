import os
import sys
import types
import unittest
from unittest.mock import patch


os.environ.setdefault("CAMPAIGN_ID", "49d28a23")
os.environ.setdefault("CAMPAIGN_PROTOCOL", "vnc")
os.environ.setdefault("INTERNAL_API_KEY", "campaign-internal-key")
os.environ.setdefault("GATEWAY_AUTH_KEY", "gateway-auth-key")
os.environ.setdefault("SESSION_TOKEN_SECRET", "session-token-secret")

config_module = types.ModuleType("config")
config_module.settings = types.SimpleNamespace(
    CAMPAIGN_ID="49d28a23",
    CAMPAIGN_PROTOCOL="vnc",
    ENVIRONMENT="production",
    INTERNAL_API_KEY="campaign-internal-key",
    STREAM_PATH="assets",
)
sys.modules.setdefault("config", config_module)

from core.stream_access import StreamAccessManager  # noqa: E402


class StreamAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_is_one_time_and_session_is_victim_scoped(self):
        manager = StreamAccessManager()
        with patch("core.stream_access.settings.CAMPAIGN_PROTOCOL", "vnc"):
            access_path = await manager.issue("49d28a23", "viewer", 60)

        parts = access_path.strip("/").split("/")
        route_handle, bootstrap = parts[1], parts[3]
        grant = await manager.consume(route_handle, bootstrap)
        self.assertIsNotNone(grant)
        self.assertEqual(grant.role, "viewer")
        self.assertIsNone(await manager.consume(route_handle, bootstrap))
        self.assertEqual(
            await manager.authorize(route_handle, grant.session_token),
            "49d28a23",
        )
        self.assertIsNone(
            await manager.authorize("deadbeef", grant.session_token)
        )
        await manager.revoke_victim("49d28a23")
        self.assertIsNone(
            await manager.authorize(route_handle, grant.session_token)
        )

    async def test_rejects_invalid_role_and_victim(self):
        manager = StreamAccessManager()
        for victim_id, role in (
            ("../escape", "viewer"),
            ("49d28a23", "admin"),
        ):
            with self.subTest(victim_id=victim_id, role=role):
                with self.assertRaises(ValueError):
                    await manager.issue(victim_id, role, 60)


if __name__ == "__main__":
    unittest.main()
