import asyncio
import unittest

from core.session_admission import SessionAdmissionController
from core.session_tokens import (
    SessionTokenError,
    issue_session_token,
    verify_session_token,
)


class SessionTokenTests(unittest.TestCase):
    def setUp(self):
        self.secret = "test-secret-that-is-not-used-in-production"

    def test_round_trip(self):
        token = issue_session_token(
            victim_id="victim-1",
            campaign_id="campaign-1",
            secret=self.secret,
            ttl_seconds=60,
            now=1_000,
        )

        claims = verify_session_token(
            token,
            campaign_id="campaign-1",
            secret=self.secret,
            now=1_001,
        )

        self.assertEqual(claims.victim_id, "victim-1")
        self.assertEqual(claims.campaign_id, "campaign-1")
        self.assertEqual(claims.expires_at, 1_060)

    def test_expired_token_is_rejected(self):
        token = issue_session_token(
            victim_id="victim-1",
            campaign_id="campaign-1",
            secret=self.secret,
            ttl_seconds=60,
            now=1_000,
        )

        with self.assertRaises(SessionTokenError):
            verify_session_token(
                token,
                campaign_id="campaign-1",
                secret=self.secret,
                now=1_060,
            )

    def test_wrong_campaign_is_rejected(self):
        token = issue_session_token(
            victim_id="victim-1",
            campaign_id="campaign-1",
            secret=self.secret,
            ttl_seconds=60,
            now=1_000,
        )

        with self.assertRaises(SessionTokenError):
            verify_session_token(
                token,
                campaign_id="campaign-2",
                secret=self.secret,
                now=1_001,
            )

    def test_tampered_token_is_rejected(self):
        token = issue_session_token(
            victim_id="victim-1",
            campaign_id="campaign-1",
            secret=self.secret,
            ttl_seconds=60,
            now=1_000,
        )
        payload, signature = token.split(".", 1)
        replacement = "A" if payload[-1] != "A" else "B"
        tampered = f"{payload[:-1]}{replacement}.{signature}"

        with self.assertRaises(SessionTokenError):
            verify_session_token(
                tampered,
                campaign_id="campaign-1",
                secret=self.secret,
                now=1_001,
            )


class SessionAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_and_capacity_are_rejected(self):
        controller = SessionAdmissionController(
            max_active_sessions=2,
            rate_limit_window_seconds=60,
            max_attempts_per_client=10,
            max_attempts_global=100,
        )

        first = await controller.reserve("victim-1", [])
        duplicate = await controller.reserve("victim-1", [])
        second = await controller.reserve("victim-2", [])
        over_capacity = await controller.reserve("victim-3", [])

        self.assertTrue(first.allowed)
        self.assertEqual(duplicate.reason, "duplicate_session")
        self.assertTrue(second.allowed)
        self.assertEqual(over_capacity.reason, "capacity")

        await controller.release("victim-1")
        retry = await controller.reserve("victim-3", [])
        self.assertTrue(retry.allowed)

    async def test_per_client_rate_limit(self):
        now = 100.0
        controller = SessionAdmissionController(
            max_active_sessions=2,
            rate_limit_window_seconds=60,
            max_attempts_per_client=2,
            max_attempts_global=100,
            clock=lambda: now,
        )

        self.assertTrue((await controller.allow_attempt("client-a")).allowed)
        self.assertTrue((await controller.allow_attempt("client-a")).allowed)
        rejected = await controller.allow_attempt("client-a")

        self.assertFalse(rejected.allowed)
        self.assertEqual(rejected.reason, "client_rate_limit")

    async def test_reservation_is_atomic(self):
        controller = SessionAdmissionController(
            max_active_sessions=5,
            rate_limit_window_seconds=60,
            max_attempts_per_client=10,
            max_attempts_global=100,
        )

        decisions = await asyncio.gather(
            controller.reserve("victim-1", []),
            controller.reserve("victim-1", []),
        )

        self.assertEqual(sum(decision.allowed for decision in decisions), 1)

    async def test_rate_limit_keys_are_pruned_and_globally_bounded(self):
        now = [100.0]
        controller = SessionAdmissionController(
            max_active_sessions=2,
            rate_limit_window_seconds=60,
            max_attempts_per_client=10,
            max_attempts_global=2,
            clock=lambda: now[0],
        )

        self.assertTrue((await controller.allow_attempt("client-a")).allowed)
        self.assertTrue((await controller.allow_attempt("client-b")).allowed)
        rejected = await controller.allow_attempt("client-c")

        self.assertEqual(rejected.reason, "global_rate_limit")
        self.assertEqual(controller.rate_limit_key_count, 3)

        now[0] += 61
        self.assertTrue((await controller.allow_attempt("client-c")).allowed)
        self.assertEqual(controller.rate_limit_key_count, 2)


if __name__ == "__main__":
    unittest.main()
