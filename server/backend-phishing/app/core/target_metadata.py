"""Asynchronous, single-flight cache for fixed campaign target metadata."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from core.favicon import fetch_public_favicon_data_uri
from utils.safe_remote import UnsafeRemoteURLError, safe_get_public_url


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TargetMetadata:
    title: str = ""
    favicon: str = ""


def fetch_target_metadata(url: str) -> TargetMetadata:
    """Fetch bounded metadata from one SSRF-validated public target."""
    if not url:
        return TargetMetadata()

    response = safe_get_public_url(
        url,
        timeout=5,
        max_bytes=1_048_576,
    )
    if response.status_code != 200:
        raise UnsafeRemoteURLError(
            f"Target metadata returned HTTP {response.status_code}"
        )

    soup = BeautifulSoup(response.text, "html.parser")
    title_tag = soup.find("title")
    title = (
        title_tag.get_text(strip=True)[:256]
        if title_tag and title_tag.get_text(strip=True)
        else ""
    )

    favicon = ""
    candidates = [urljoin(url, "favicon.ico")]
    icon_link = soup.find(
        "link",
        rel=lambda value: value and "icon" in str(value).lower(),
    )
    if icon_link and icon_link.get("href"):
        linked_icon = urljoin(url, str(icon_link["href"]))
        if linked_icon not in candidates:
            candidates.append(linked_icon)

    for candidate in candidates:
        try:
            favicon = fetch_public_favicon_data_uri(candidate)
            break
        except (UnsafeRemoteURLError, TypeError, ValueError):
            continue

    return TargetMetadata(title=title, favicon=favicon)


class TargetMetadataCache:
    """Cache target metadata and collapse concurrent refreshes into one fetch."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 3600,
        failure_ttl_seconds: int = 30,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.failure_ttl_seconds = failure_ttl_seconds
        self._url = ""
        self._metadata = TargetMetadata()
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, url: str) -> TargetMetadata:
        now = time.monotonic()
        if self._url == url and now < self._expires_at:
            return self._metadata

        async with self._lock:
            now = time.monotonic()
            if self._url == url and now < self._expires_at:
                return self._metadata

            try:
                metadata = await asyncio.to_thread(fetch_target_metadata, url)
                ttl = self.ttl_seconds
            except (UnsafeRemoteURLError, TypeError, ValueError):
                logger.warning(
                    "Target title/favicon refresh failed; retrying after cooldown"
                )
                metadata = TargetMetadata()
                ttl = self.failure_ttl_seconds

            self._url = url
            self._metadata = metadata
            self._expires_at = time.monotonic() + ttl
            return metadata


target_metadata_cache = TargetMetadataCache()
