"""Server-side browser sessions for clean campaign landing URLs."""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import time


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LandingAccessManager:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    async def issue(self, tracking_id: str, ttl_seconds: int = 86400) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        async with self._lock:
            self._tokens = {
                key: value
                for key, value in self._tokens.items()
                if value[1] > now
            }
            self._tokens[_digest(token)] = (
                tracking_id,
                now + max(30, min(ttl_seconds, 86400)),
            )
        return token

    async def resolve(self, token: str | None) -> str | None:
        if not token:
            return None
        now = time.time()
        async with self._lock:
            value = self._tokens.get(_digest(token))
            if value is None or value[1] <= now:
                return None
            return value[0]


landing_access = LandingAccessManager()
