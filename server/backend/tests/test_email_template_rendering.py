import unittest
from types import SimpleNamespace

from utils.email_sender import (
    EmailSender,
    inject_tracking_pixel,
    sanitize_email_header,
)


def sender() -> EmailSender:
    return EmailSender(
        SimpleNamespace(
            ignore_cert_errors=False,
        )
    )


def victim(**overrides):
    values = {
        "first_name": "Alice",
        "last_name": "Example",
        "email": "alice@example.test",
        "position": "Engineer",
        "company": "Example",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class EmailTemplateRenderingTests(unittest.TestCase):
    def test_tracking_pixel_is_inserted_before_closing_body(self):
        rendered = inject_tracking_pixel(
            "<html><body><p>Hello</p></body></html>",
            "https://campaign.example.test/p/tracking.png?a=1&b=2",
        )

        pixel_position = rendered.index('<img src="https://campaign.example.test')
        self.assertLess(pixel_position, rendered.index("</body>"))
        self.assertIn("a=1&amp;b=2", rendered)
        self.assertFalse(rendered.endswith("</html><img"))

    def test_tracking_pixel_falls_back_for_html_fragments(self):
        rendered = inject_tracking_pixel(
            "<p>Hello</p>",
            "https://campaign.example.test/p/tracking.png",
        )

        self.assertTrue(rendered.startswith("<p>Hello</p><img "))

    def test_html_context_escapes_recipient_values_and_urls(self):
        rendered = sender()._replace_variables(
            '<p title="{{company}}">{{first_name}} {{tracking_url}}</p>',
            victim=victim(
                first_name="<script>alert(1)</script>",
                company='" onmouseover="alert(1)',
            ),
            tracking_url="https://example.test/?a=1&b=2",
            tracking_pixel="https://example.test/pixel?a=1&b=2",
            context="html",
        )

        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&quot; onmouseover=&quot;", rendered)
        self.assertIn("?a=1&amp;b=2", rendered)

    def test_text_context_preserves_readable_plain_text(self):
        rendered = sender()._replace_variables(
            "Hello {{first_name}}: {{tracking_url}}",
            victim=victim(first_name="A&B"),
            tracking_url="https://example.test/?a=1&b=2",
            tracking_pixel="",
            context="text",
        )

        self.assertEqual(
            rendered,
            "Hello A&B: https://example.test/?a=1&b=2",
        )

    def test_header_context_removes_line_breaks_and_controls(self):
        rendered = sender()._replace_variables(
            "Hello {{first_name}}",
            victim=victim(first_name="Alice\r\nBcc: attacker@example.test"),
            tracking_url="",
            tracking_pixel="",
            context="header",
        )

        self.assertNotIn("\r", rendered)
        self.assertNotIn("\n", rendered)
        self.assertEqual(
            rendered,
            "Hello Alice Bcc: attacker@example.test",
        )
        self.assertEqual(
            sanitize_email_header("Sender\r\nInjected"),
            "Sender Injected",
        )


if __name__ == "__main__":
    unittest.main()
