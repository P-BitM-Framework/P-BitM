"""In-memory sliding-window lockout for the admin login endpoint."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Callable


class LoginRateLimiter:
    """Atomically consume login-attempt budgets for an IP and username."""

    def __init__(
        self,
        *,
        window_seconds: int = 300,
        max_attempts_per_ip: int = 20,
        max_attempts_per_username: int = 8,
        clock: Callable[[], float] = time.monotonic,
    ):
        if min(window_seconds, max_attempts_per_ip, max_attempts_per_username) <= 0:
            raise ValueError("Rate limit parameters must be positive")

        self.window_seconds = window_seconds
        self.max_attempts_per_ip = max_attempts_per_ip
        self.max_attempts_per_username = max_attempts_per_username
        self._clock = clock
        self._attempts: dict[str, deque[float]] = {}
        self._cleanup_interval = min(float(window_seconds), 60.0)
        self._next_cleanup = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def _user_key(username: str) -> str:
        return f"user:{username.strip().casefold()}"

    def _prune(self, key: str, now: float) -> deque[float] | None:
        attempts = self._attempts.get(key)
        if attempts is None:
            return None
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if not attempts:
            self._attempts.pop(key, None)
            return None
        return attempts

    def _cleanup_expired(self, now: float) -> None:
        if now < self._next_cleanup:
            return
        for key in list(self._attempts):
            self._prune(key, now)
        self._next_cleanup = now + self._cleanup_interval

    async def record_attempt_if_allowed(self, *, ip: str, username: str) -> bool:
        now = self._clock()
        async with self._lock:
            self._cleanup_expired(now)
            ip_key = f"ip:{ip or 'unknown'}"
            user_key = self._user_key(username)
            ip_attempts = self._prune(ip_key, now)
            user_attempts = self._prune(user_key, now)
            if (
                len(ip_attempts or ()) >= self.max_attempts_per_ip
                or len(user_attempts or ()) >= self.max_attempts_per_username
            ):
                return False
            self._attempts.setdefault(ip_key, deque()).append(now)
            self._attempts.setdefault(user_key, deque()).append(now)
            return True

    async def record_success(self, *, ip: str, username: str) -> None:
        async with self._lock:
            self._attempts.pop(self._user_key(username), None)
