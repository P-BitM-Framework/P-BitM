"""Safe, target-shaped public campaign routes."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse


def derive_entry_path(target_url: str) -> str:
    """Return a safe public path shaped like the selected target pathname."""
    decoded_path = unquote(urlparse(target_url).path)
    segments: list[str] = []
    for raw_segment in decoded_path.split("/"):
        if not raw_segment or raw_segment in {".", ".."}:
            continue
        segment = re.sub(r"[^A-Za-z0-9._~-]+", "-", raw_segment).strip("-")
        if segment:
            segments.append(segment[:64])
    return "/".join(segments)[:256].rstrip("/")


def build_public_access_url(public_url: str, access_path: str) -> str:
    """Join a gateway-owned absolute path to the campaign public origin."""
    parsed = urlparse(public_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Invalid campaign public URL")
    if not access_path.startswith("/"):
        raise ValueError("Stream access path must be absolute")
    return f"{parsed.scheme}://{parsed.netloc}{access_path}"
