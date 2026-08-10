import asyncio
import unittest

from utils.login_rate_limiter import LoginRateLimiter


class LoginRateLimiterTests(unittest.TestCase):
    def test_rejects_construction_with_non_positive_limits(self):
        with self.assertRaises(ValueError):
            LoginRateLimiter(window_seconds=0)
        with self.assertRaises(ValueError):
            LoginRateLimiter(max_attempts_per_ip=0)
        with self.assertRaises(ValueError):
            LoginRateLimiter(max_attempts_per_username=0)

    def test_locks_out_after_too_many_failures_for_same_username(self):
        limiter = LoginRateLimiter(
            window_seconds=60, max_attempts_per_ip=100, max_attempts_per_username=3
        )

        async def scenario():
            for _ in range(3):
                self.assertTrue(
                    await limiter.record_attempt_if_allowed(
                        ip="192.0.2.1",
                        username="admin",
                    )
                )
            return await limiter.record_attempt_if_allowed(
                ip="192.0.2.1",
                username="admin",
            )

        self.assertFalse(asyncio.run(scenario()))

    def test_lockout_is_scoped_per_username_not_shared(self):
        limiter = LoginRateLimiter(
            window_seconds=60, max_attempts_per_ip=100, max_attempts_per_username=2
        )

        async def scenario():
            await limiter.record_attempt_if_allowed(ip="192.0.2.1", username="alice")
            await limiter.record_attempt_if_allowed(ip="192.0.2.1", username="alice")
            alice_allowed = await limiter.record_attempt_if_allowed(
                ip="192.0.2.1",
                username="alice",
            )
            bob_allowed = await limiter.record_attempt_if_allowed(
                ip="192.0.2.1",
                username="bob",
            )
            return alice_allowed, bob_allowed

        alice_allowed, bob_allowed = asyncio.run(scenario())
        self.assertFalse(alice_allowed)
        self.assertTrue(bob_allowed)

    def test_locks_out_by_ip_even_across_different_usernames(self):
        limiter = LoginRateLimiter(
            window_seconds=60, max_attempts_per_ip=2, max_attempts_per_username=100
        )

        async def scenario():
            await limiter.record_attempt_if_allowed(ip="192.0.2.2", username="alice")
            await limiter.record_attempt_if_allowed(ip="192.0.2.2", username="bob")
            return await limiter.record_attempt_if_allowed(
                ip="192.0.2.2",
                username="carol",
            )

        self.assertFalse(asyncio.run(scenario()))

    def test_successful_login_clears_the_failure_history(self):
        limiter = LoginRateLimiter(
            window_seconds=60, max_attempts_per_ip=100, max_attempts_per_username=2
        )

        async def scenario():
            await limiter.record_attempt_if_allowed(ip="192.0.2.3", username="admin")
            await limiter.record_success(ip="192.0.2.3", username="admin")
            return await limiter.record_attempt_if_allowed(
                ip="192.0.2.3",
                username="admin",
            )

        self.assertTrue(asyncio.run(scenario()))

    def test_attempts_expire_after_the_window_elapses(self):
        current_time = [0.0]
        limiter = LoginRateLimiter(
            window_seconds=10,
            max_attempts_per_ip=100,
            max_attempts_per_username=1,
            clock=lambda: current_time[0],
        )

        async def scenario():
            await limiter.record_attempt_if_allowed(ip="192.0.2.4", username="admin")
            still_locked = not await limiter.record_attempt_if_allowed(
                ip="192.0.2.4",
                username="admin",
            )
            current_time[0] += 11
            recovered = await limiter.record_attempt_if_allowed(
                ip="192.0.2.4",
                username="admin",
            )
            return still_locked, recovered

        still_locked, recovered = asyncio.run(scenario())
        self.assertTrue(still_locked)
        self.assertTrue(recovered)

    def test_success_does_not_clear_the_ip_budget(self):
        limiter = LoginRateLimiter(
            window_seconds=60,
            max_attempts_per_ip=2,
            max_attempts_per_username=100,
        )

        async def scenario():
            await limiter.record_attempt_if_allowed(ip="192.0.2.5", username="known")
            await limiter.record_success(ip="192.0.2.5", username="known")
            await limiter.record_attempt_if_allowed(ip="192.0.2.5", username="victim")
            return await limiter.record_attempt_if_allowed(
                ip="192.0.2.5",
                username="another",
            )

        self.assertFalse(asyncio.run(scenario()))

    def test_concurrent_attempts_cannot_exceed_the_budget(self):
        limiter = LoginRateLimiter(
            window_seconds=60,
            max_attempts_per_ip=5,
            max_attempts_per_username=5,
        )

        async def scenario():
            return await asyncio.gather(
                *(
                    limiter.record_attempt_if_allowed(
                        ip="192.0.2.6",
                        username="admin",
                    )
                    for _ in range(50)
                )
            )

        results = asyncio.run(scenario())
        self.assertEqual(sum(results), 5)

    def test_periodic_cleanup_removes_inactive_keys(self):
        current_time = [0.0]
        limiter = LoginRateLimiter(
            window_seconds=10,
            max_attempts_per_ip=100,
            max_attempts_per_username=100,
            clock=lambda: current_time[0],
        )

        async def scenario():
            await limiter.record_attempt_if_allowed(ip="192.0.2.7", username="expired")
            current_time[0] = 11.0
            await limiter.record_attempt_if_allowed(ip="192.0.2.8", username="current")

        asyncio.run(scenario())
        self.assertNotIn("ip:192.0.2.7", limiter._attempts)
        self.assertNotIn("user:expired", limiter._attempts)


if __name__ == "__main__":
    unittest.main()
