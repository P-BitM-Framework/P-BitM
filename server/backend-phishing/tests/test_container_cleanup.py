import os
import unittest
from unittest.mock import AsyncMock, patch


TEST_ENV = {
    "CAMPAIGN_ID": "49d28a23",
    "CAMPAIGN_PROTOCOL": "selkies",
    "INTERNAL_API_KEY": "campaign-internal-key",
    "GATEWAY_AUTH_KEY": "gateway-auth-key",
    "SESSION_TOKEN_SECRET": "session-token-secret",
    "DB_PATH": "/tmp/pbitm-container-cleanup-test.db",
}

with patch.dict(os.environ, TEST_ENV):
    from routes.public import _cleanup_victim_container  # noqa: E402


class VictimContainerCleanupTests(unittest.IsolatedAsyncioTestCase):
    @patch("routes.public.ws_manager.is_victim_connected", return_value=False)
    @patch("routes.public.destroy_victim_container", new_callable=AsyncMock)
    @patch("routes.public.dump_victim_container", new_callable=AsyncMock)
    async def test_dumps_before_removing_a_disconnected_session(
        self,
        dump_profile,
        destroy_container,
        _is_connected,
    ):
        await _cleanup_victim_container("victim", persist_profile=True)

        dump_profile.assert_awaited_once_with("victim")
        destroy_container.assert_awaited_once_with("victim")

    @patch("routes.public.logger.exception")
    @patch("routes.public.ws_manager.is_victim_connected", return_value=False)
    @patch("routes.public.destroy_victim_container", new_callable=AsyncMock)
    @patch(
        "routes.public.dump_victim_container",
        new_callable=AsyncMock,
        side_effect=RuntimeError("dump failed"),
    )
    async def test_preserves_the_container_when_the_dump_fails(
        self,
        dump_profile,
        destroy_container,
        is_connected,
        _log_exception,
    ):
        await _cleanup_victim_container("victim", persist_profile=True)

        dump_profile.assert_awaited_once_with("victim")
        is_connected.assert_not_called()
        destroy_container.assert_not_awaited()

    @patch("routes.public.ws_manager.is_victim_connected", return_value=True)
    @patch("routes.public.destroy_victim_container", new_callable=AsyncMock)
    @patch("routes.public.dump_victim_container", new_callable=AsyncMock)
    async def test_preserves_a_session_that_reconnects_during_the_dump(
        self,
        dump_profile,
        destroy_container,
        is_connected,
    ):
        await _cleanup_victim_container("victim", persist_profile=True)

        dump_profile.assert_awaited_once_with("victim")
        is_connected.assert_called_once_with("victim")
        destroy_container.assert_not_awaited()

    @patch("routes.public.ws_manager.is_victim_connected", return_value=False)
    @patch("routes.public.destroy_victim_container", new_callable=AsyncMock)
    @patch("routes.public.dump_victim_container", new_callable=AsyncMock)
    async def test_cleans_up_a_failed_startup_without_dumping(
        self,
        dump_profile,
        destroy_container,
        _is_connected,
    ):
        await _cleanup_victim_container("victim", persist_profile=False)

        dump_profile.assert_not_awaited()
        destroy_container.assert_awaited_once_with("victim")


if __name__ == "__main__":
    unittest.main()
