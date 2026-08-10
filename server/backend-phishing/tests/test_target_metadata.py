import asyncio
import unittest
from unittest.mock import patch

from core.target_metadata import (
    TargetMetadata,
    TargetMetadataCache,
)


class TargetMetadataCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_reuses_successful_metadata_until_expiry(self):
        cache = TargetMetadataCache(ttl_seconds=60)
        expected = TargetMetadata("Target", "data:image/png;base64,AA==")

        with patch(
            "core.target_metadata.fetch_target_metadata",
            return_value=expected,
        ) as fetch:
            first = await cache.get("https://target.example/")
            second = await cache.get("https://target.example/")

        self.assertEqual(first, expected)
        self.assertEqual(second, expected)
        fetch.assert_called_once_with("https://target.example/")

    async def test_collapses_concurrent_refreshes(self):
        cache = TargetMetadataCache(ttl_seconds=60)
        expected = TargetMetadata("Target", "")

        def fetch(_url):
            return expected

        with patch(
            "core.target_metadata.fetch_target_metadata",
            side_effect=fetch,
        ) as mocked_fetch:
            results = await asyncio.gather(
                *[
                    cache.get("https://target.example/")
                    for _ in range(10)
                ]
            )

        self.assertEqual(results, [expected] * 10)
        mocked_fetch.assert_called_once()

    async def test_retries_failures_after_short_cooldown(self):
        cache = TargetMetadataCache(
            ttl_seconds=60,
            failure_ttl_seconds=0,
        )

        with patch(
            "core.target_metadata.fetch_target_metadata",
            side_effect=ValueError("unavailable"),
        ) as fetch:
            self.assertEqual(
                await cache.get("https://target.example/"),
                TargetMetadata(),
            )
            self.assertEqual(
                await cache.get("https://target.example/"),
                TargetMetadata(),
            )

        self.assertEqual(fetch.call_count, 2)


if __name__ == "__main__":
    unittest.main()
