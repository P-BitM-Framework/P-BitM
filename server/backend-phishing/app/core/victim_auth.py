"""Credentials scoped to a single victim container."""

import base64
import hashlib
import hmac


def derive_victim_api_key(campaign_key: str, victim_id: str) -> str:
    if not campaign_key or not victim_id:
        raise ValueError("campaign_key and victim_id are required")

    digest = hmac.new(
        campaign_key.encode("utf-8"),
        f"pbitm:victim:{victim_id}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def derive_selkies_master_token(campaign_key: str, victim_id: str) -> str:
    """Derive the private control-plane credential for one Selkies instance."""
    if not campaign_key or not victim_id:
        raise ValueError("campaign_key and victim_id are required")

    digest = hmac.new(
        campaign_key.encode("utf-8"),
        f"pbitm:selkies-control:{victim_id}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
