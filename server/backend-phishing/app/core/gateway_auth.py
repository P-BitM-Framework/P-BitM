"""Authorization checks used by the campaign nginx victim gateway."""

from __future__ import annotations

import re
import secrets
from collections.abc import Collection


VICTIM_ID_PATTERN = re.compile(r"^[0-9a-f]{8}$")


def is_gateway_request_authorized(
    victim_id: str | None,
    provided_key: str | None,
    expected_key: str,
    active_victims: Collection[str],
) -> bool:
    if not provided_key or not secrets.compare_digest(provided_key, expected_key):
        return False
    return bool(
        victim_id
        and VICTIM_ID_PATTERN.fullmatch(victim_id)
        and victim_id in active_victims
    )
