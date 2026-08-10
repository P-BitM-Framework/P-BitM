import json
import unittest

from core.websocket_messages import (
    ClientMessageError,
    WebSocketMessageLimiter,
    parse_collected_info,
    parse_structured_client_message,
)


class WebSocketMessageLimiterTests(unittest.TestCase):
    def test_rejects_oversized_messages(self):
        limiter = WebSocketMessageLimiter(
            max_message_bytes=8,
            window_seconds=10,
            max_messages=10,
        )

        decision = limiter.check("123456789")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "message_too_large")

    def test_rate_limit_resets_after_window(self):
        now = [100.0]
        limiter = WebSocketMessageLimiter(
            max_message_bytes=100,
            window_seconds=10,
            max_messages=2,
            clock=lambda: now[0],
        )

        self.assertTrue(limiter.check("one").allowed)
        self.assertTrue(limiter.check("two").allowed)
        self.assertEqual(
            limiter.check("three").reason,
            "message_rate_limit",
        )

        now[0] += 11
        self.assertTrue(limiter.check("four").allowed)


class StructuredWebSocketMessageTests(unittest.TestCase):
    def test_accepts_valid_offer_and_candidate(self):
        offer = parse_structured_client_message(json.dumps({
            "type": "webrtc-offer",
            "session_id": "webcam-session-1234567890",
            "offer": {
                "type": "offer",
                "sdp": "v=0\r\n",
            },
        }))
        candidate = parse_structured_client_message(json.dumps({
            "type": "webrtc-candidate",
            "session_id": "webcam-session-1234567890",
            "candidate": {
                "candidate": "candidate:1 1 UDP 1 203.0.113.1 1234 typ host",
                "sdpMid": "0",
                "sdpMLineIndex": 0,
                "usernameFragment": None,
            },
        }))
        webcam_error = parse_structured_client_message(json.dumps({
            "type": "webcam-error",
            "session_id": "webcam-session-1234567890",
            "code": "permission-denied",
        }))

        self.assertEqual(offer["type"], "webrtc-offer")
        self.assertEqual(candidate["type"], "webrtc-candidate")
        self.assertEqual(webcam_error["code"], "permission-denied")

    def test_rejects_unknown_or_malformed_json_messages(self):
        messages = (
            "{broken",
            json.dumps({"type": "unknown"}),
            json.dumps({
                "type": "webrtc-offer",
                "session_id": "webcam-session-1234567890",
                "offer": {"type": "answer", "sdp": "v=0"},
            }),
            json.dumps({
                "type": "webrtc-candidate",
                "session_id": "webcam-session-1234567890",
                "candidate": {"candidate": ""},
            }),
            json.dumps({
                "type": "webcam-error",
                "session_id": "short",
                "code": "permission-denied",
            }),
        )

        for message in messages:
            with self.subTest(message=message), self.assertRaises(
                ClientMessageError
            ):
                parse_structured_client_message(message)

    def test_ordinary_text_is_not_treated_as_structured_json(self):
        self.assertIsNone(parse_structured_client_message("pong"))
        self.assertIsNone(parse_structured_client_message("[HTML RECEIVED] ok"))

    def test_collected_info_must_be_an_object(self):
        result = parse_collected_info(
            '[COLLECTED INFO] {"user_agent": "test"}'
        )
        self.assertEqual(result, {"user_agent": "test"})

        with self.assertRaises(ClientMessageError):
            parse_collected_info("[COLLECTED INFO] []")


if __name__ == "__main__":
    unittest.main()
