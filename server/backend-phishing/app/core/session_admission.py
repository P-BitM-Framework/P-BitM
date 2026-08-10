"""Concurrency-safe admission controls for public browser sessions."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Collection


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    reason: str | None = None


class SessionAdmissionController:
    def __init__(
        self,
        *,
        max_active_sessions: int,
        rate_limit_window_seconds: int,
        max_attempts_per_client: int,
        max_attempts_global: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        if min(
            max_active_sessions,
            rate_limit_window_seconds,
            max_attempts_per_client,
            max_attempts_global,
        ) <= 0:
            raise ValueError("Admission limits must be positive")

        self.max_active_sessions = max_active_sessions
        self.rate_limit_window_seconds = rate_limit_window_seconds
        self.max_attempts_per_client = max_attempts_per_client
        self.max_attempts_global = max_attempts_global
        self._clock = clock
        self._attempts: dict[str, deque[float]] = {}
        self._pending_victims: set[str] = set()
        self._lock = asyncio.Lock()

    @property
    def rate_limit_key_count(self) -> int:
        return len(self._attempts)

    def _prune_attempts(self, now: float) -> None:
        cutoff = now - self.rate_limit_window_seconds
        for key, attempts in list(self._attempts.items()):
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if not attempts:
                self._attempts.pop(key, None)

    def _record_attempt(self, key: str, limit: int, now: float) -> bool:
        attempts = self._attempts.setdefault(key, deque())
        if len(attempts) >= limit:
            return False
        attempts.append(now)
        return True

    async def allow_attempt(self, client_key: str) -> AdmissionDecision:
        now = self._clock()
        async with self._lock:
            self._prune_attempts(now)
            global_allowed = self._record_attempt(
                "__global__", self.max_attempts_global, now
            )
            if not global_allowed:
                return AdmissionDecision(False, "global_rate_limit")
            client_allowed = self._record_attempt(
                f"client:{client_key or 'unknown'}",
                self.max_attempts_per_client,
                now,
            )

        if not client_allowed:
            return AdmissionDecision(False, "client_rate_limit")
        return AdmissionDecision(True)

    async def reserve(
        self,
        victim_id: str,
        active_victim_ids: Collection[str],
    ) -> AdmissionDecision:
        async with self._lock:
            if victim_id in active_victim_ids or victim_id in self._pending_victims:
                return AdmissionDecision(False, "duplicate_session")

            if len(active_victim_ids) + len(self._pending_victims) >= self.max_active_sessions:
                return AdmissionDecision(False, "capacity")

            self._pending_victims.add(victim_id)
            return AdmissionDecision(True)

    async def release(self, victim_id: str | None) -> None:
        if not victim_id:
            return
        async with self._lock:
            self._pending_victims.discard(victim_id)
