import base64
import struct
import unittest

from core.favicon import (
    MAX_FAVICON_DECODED_BYTES,
    detect_favicon_media_type,
    extract_largest_png_from_ico,
    favicon_bytes_to_data_uri,
    remove_empty_favicon_placeholders,
    validate_favicon_data_uri,
    validate_favicon_url,
)


class FaviconValidationTests(unittest.TestCase):
    def test_encodes_safe_image_as_inline_data(self):
        content = b"\x89PNG\r\n\x1a\n" + b"x" * 128

        result = favicon_bytes_to_data_uri(content, "image/png")

        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertEqual(
            base64.b64decode(result.split(",", 1)[1]),
            content,
        )

    def test_rejects_remote_and_active_content(self):
        for value in (
            "https://target.example/favicon.ico",
            "data:image/svg+xml;base64,PHN2Zy8+",
            "javascript:alert(1)",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_favicon_data_uri(value)

    def test_rejects_oversized_image_bytes(self):
        with self.assertRaises(ValueError):
            favicon_bytes_to_data_uri(
                b"\x89PNG\r\n\x1a\n"
                + b"x" * (MAX_FAVICON_DECODED_BYTES + 1),
                "image/png",
            )

    def test_rejects_spoofed_image_content(self):
        encoded = base64.b64encode(b"<html>not an image</html>").decode()

        with self.assertRaises(ValueError):
            validate_favicon_data_uri(f"data:image/png;base64,{encoded}")
        with self.assertRaises(ValueError):
            favicon_bytes_to_data_uri(
                b"<svg onload='alert(1)'/>",
                "image/png",
            )

    def test_detects_supported_favicon_signatures(self):
        samples = {
            b"\x89PNG\r\n\x1a\npayload": "image/png",
            b"\xff\xd8\xffpayload": "image/jpeg",
            b"GIF89apayload": "image/gif",
            b"RIFF\x04\x00\x00\x00WEBPpayload": "image/webp",
            b"\x00\x00\x01\x00payload": "image/x-icon",
        }

        for content, expected in samples.items():
            with self.subTest(expected=expected):
                self.assertEqual(detect_favicon_media_type(content), expected)

    def test_normalizes_png_backed_ico_using_actual_png_dimensions(self):
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        directory_size = 6 + 16
        ico = (
            struct.pack("<HHH", 0, 1, 1)
            # Zero width/height means 256x256 in an ICO directory, even
            # though this embedded PNG's IHDR correctly says 1x1.
            + struct.pack(
                "<BBBBHHII",
                0,
                0,
                0,
                0,
                1,
                32,
                len(png),
                directory_size,
            )
            + png
        )

        self.assertEqual(extract_largest_png_from_ico(ico), png)
        encoded_ico = base64.b64encode(ico).decode("ascii")
        result = validate_favicon_data_uri(
            f"data:image/x-icon;base64,{encoded_ico}"
        )

        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(result.split(",", 1)[1]), png)

    def test_accepts_only_credential_free_http_favicon_urls(self):
        self.assertEqual(
            validate_favicon_url("https://target.example/favicon.ico"),
            "https://target.example/favicon.ico",
        )
        for value in (
            "javascript:alert(1)",
            "file:///etc/passwd",
            "https://user:password@target.example/favicon.ico",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_favicon_url(value)

    def test_removes_empty_favicon_elements_from_landing_page(self):
        html = """
        <link rel='icon' href='FAVICON'>
        <img src=FAVICON class="heading-favicon" alt="Icon">
        <span>FAVICON</span>
        """

        result = remove_empty_favicon_placeholders(html)

        self.assertNotIn("<link", result)
        self.assertNotIn("<img", result)
        self.assertIn("<span>FAVICON</span>", result)


if __name__ == "__main__":
    unittest.main()
