"""Short-lived, campaign-local tokens used to authorize public WebSockets."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass


class SessionTokenError(ValueError):
    """Raised when a session token is malformed, invalid, or expired."""


@dataclass(frozen=True)
class SessionTokenClaims:
    victim_id: str
    campaign_id: str
    expires_at: int
    token_id: str


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception as exc:
        raise SessionTokenError("Malformed session token") from exc


def issue_session_token(
    *,
    victim_id: str,
    campaign_id: str,
    secret: str,
    ttl_seconds: int,
    now: int | None = None,
) -> str:
    if not victim_id or not campaign_id or not secret:
        raise ValueError("victim_id, campaign_id, and secret are required")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")

    issued_at = int(time.time() if now is None else now)
    payload = {
        "v": 1,
        "sub": victim_id,
        "cid": campaign_id,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": secrets.token_urlsafe(12),
    }
    encoded_payload = _encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def verify_session_token(
    token: str,
    *,
    campaign_id: str,
    secret: str,
    now: int | None = None,
) -> SessionTokenClaims:
    if not token or len(token) > 2048:
        raise SessionTokenError("Malformed session token")

    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise SessionTokenError("Malformed session token") from exc

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    provided_signature = _decode(encoded_signature)
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise SessionTokenError("Invalid session token")

    try:
        payload = json.loads(_decode(encoded_payload))
        version = payload["v"]
        victim_id = payload["sub"]
        token_campaign_id = payload["cid"]
        expires_at = int(payload["exp"])
        token_id = payload["jti"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SessionTokenError("Malformed session token") from exc

    current_time = int(time.time() if now is None else now)
    if version != 1 or token_campaign_id != campaign_id:
        raise SessionTokenError("Invalid session token")
    if not isinstance(victim_id, str) or not victim_id:
        raise SessionTokenError("Invalid session token")
    if not isinstance(token_id, str) or not token_id:
        raise SessionTokenError("Invalid session token")
    if expires_at <= current_time:
        raise SessionTokenError("Expired session token")

    return SessionTokenClaims(
        victim_id=victim_id,
        campaign_id=token_campaign_id,
        expires_at=expires_at,
        token_id=token_id,
    )
