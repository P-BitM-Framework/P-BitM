import unittest
import base64

from pydantic import ValidationError

from core.request_models import (
    EventProxyRequest,
    ModuleDataRequest,
    SiteInfoRequest,
    VictimDataRequest,
)


class CampaignCallbackValidationTests(unittest.TestCase):
    def test_rejects_artifact_traversal(self):
        with self.assertRaises(ValidationError):
            VictimDataRequest(
                data_type="screenshot",
                file_path="../outside.png",
            )

    def test_preserves_supported_extra_metadata_contract(self):
        request = VictimDataRequest(
            data_type="keylog",
            file_path="keylogs.txt",
            file_size_bytes=10,
            extra_metadata={"source": "browser"},
        )

        self.assertEqual(
            request.normalized_metadata(),
            {"source": "browser"},
        )

    def test_public_collection_accepts_only_module_data(self):
        with self.assertRaises(ValidationError):
            ModuleDataRequest(
                data_type="screenshot",
                module_id="module01",
                metadata={},
            )

    def test_event_type_must_be_known(self):
        with self.assertRaises(ValidationError):
            EventProxyRequest(
                event_type="arbitrary_event",
                payload={},
            )

    def test_bulk_cookie_capture_is_supported(self):
        request = EventProxyRequest(
            event_type="cookie_captured",
            timestamp="2026-07-26T08:15:30Z",
            payload={"cookies": []},
        )

        self.assertEqual(request.event_type, "cookie_captured")

    def test_site_info_accepts_bounded_image_data_favicon(self):
        favicon = (
            "data:image/png;base64,"
            + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 4096).decode()
        )

        request = SiteInfoRequest(title="Example", favicon=favicon)

        self.assertEqual(request.title, "Example")
        self.assertEqual(request.favicon, favicon)

    def test_site_info_rejects_active_favicon_data_type(self):
        favicon = (
            "data:image/svg+xml;base64,"
            + base64.b64encode(b"<svg onload='alert(1)'/>").decode()
        )

        with self.assertRaises(ValidationError):
            SiteInfoRequest(title="Example", favicon=favicon)

    def test_site_info_accepts_remote_favicon_url(self):
        request = SiteInfoRequest(
            title="Example",
            favicon="https://target.example/favicon.ico",
        )

        self.assertEqual(
            request.favicon,
            "https://target.example/favicon.ico",
        )

    def test_site_info_rejects_unsafe_remote_favicon_url(self):
        for favicon in (
            "javascript:alert(1)",
            "file:///etc/passwd",
            "https://user:password@target.example/favicon.ico",
        ):
            with self.subTest(favicon=favicon), self.assertRaises(ValidationError):
                SiteInfoRequest(title="Example", favicon=favicon)

    def test_site_info_rejects_oversized_decoded_favicon(self):
        favicon = (
            "data:image/png;base64,"
            + base64.b64encode(b"x" * (190 * 1024 + 1)).decode()
        )

        with self.assertRaises(ValidationError):
            SiteInfoRequest(title="Example", favicon=favicon)
