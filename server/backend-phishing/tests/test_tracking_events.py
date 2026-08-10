import asyncio
import unittest

from core.tracking_events import (
    TrackingEvent,
    TrackingEventDispatcher,
    TrackingRateLimiter,
    is_valid_tracking_id,
)


class TrackingEventValidationTests(unittest.TestCase):
    def test_accepts_generated_tracking_id_formats(self):
        for value in (
            "H5g2kYx-PQ4_mN8v7aBcDg",
            "98f4ebd6-35b3-47a7-b236-36e5527675dc",
        ):
            with self.subTest(value=value):
                self.assertTrue(is_valid_tracking_id(value))

    def test_rejects_malformed_tracking_ids(self):
        for value in ("", "short", "../escape", "token/with/path", "x" * 129):
            with self.subTest(value=value):
                self.assertFalse(is_valid_tracking_id(value))


class TrackingRateLimiterTests(unittest.IsolatedAsyncioTestCase):
    async def test_enforces_client_and_global_limits(self):
        now = [100.0]
        limiter = TrackingRateLimiter(
            window_seconds=60,
            max_per_client=2,
            max_global=3,
            clock=lambda: now[0],
        )

        self.assertTrue(await limiter.allow("client-a"))
        self.assertTrue(await limiter.allow("client-a"))
        self.assertFalse(await limiter.allow("client-a"))
        self.assertTrue(await limiter.allow("client-b"))
        self.assertFalse(await limiter.allow("client-c"))

        now[0] += 61
        self.assertTrue(await limiter.allow("client-a"))


class TrackingDispatcherTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def event(tracking_id: str) -> TrackingEvent:
        return TrackingEvent(
            endpoint="/api/tracking/email-opened",
            tracking_id=tracking_id,
            ip_address="203.0.113.10",
            user_agent="test",
        )

    async def test_queue_capacity_is_bounded(self):
        dispatcher = TrackingEventDispatcher(
            admin_api_url="http://admin",
            internal_api_key="key",
            campaign_id="campaign",
            queue_size=1,
            worker_count=1,
        )

        self.assertTrue(dispatcher.enqueue(self.event("tracking-a")))
        self.assertFalse(dispatcher.enqueue(self.event("tracking-b")))
        self.assertEqual(dispatcher.queue_size, 1)

    async def test_fixed_worker_delivers_queued_event(self):
        delivered = []

        async def sender(event):
            delivered.append(event)

        dispatcher = TrackingEventDispatcher(
            admin_api_url="http://admin",
            internal_api_key="key",
            campaign_id="campaign",
            queue_size=2,
            worker_count=1,
            sender=sender,
        )
        await dispatcher.start()
        try:
            self.assertTrue(dispatcher.enqueue(self.event("tracking-a")))
            await asyncio.wait_for(dispatcher._queue.join(), timeout=1)
        finally:
            await dispatcher.stop()

        self.assertEqual(
            [event.tracking_id for event in delivered],
            ["tracking-a"],
        )


if __name__ == "__main__":
    unittest.main()
