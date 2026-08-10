import unittest

from bs4 import BeautifulSoup

from utils.landing_page import process_landing_page


class LandingPageStreamPermissionsTests(unittest.TestCase):
    def test_injected_stream_iframe_delegates_shared_clipboard(self):
        rendered = process_landing_page(
            "<html><head></head><body><main class='main-wrapper'></main></body></html>",
            "campaign",
        )
        iframe = BeautifulSoup(rendered, "html.parser").select_one(
            "iframe.iframe-visible"
        )

        permissions = iframe.get("allow", "").split("; ")
        self.assertIn("clipboard-read", permissions)
        self.assertIn("clipboard-write", permissions)

    def test_existing_stream_iframe_permissions_are_normalized(self):
        rendered = process_landing_page(
            """
            <html><body>
              <iframe class="iframe-visible" allow="camera"></iframe>
              <main class="main-wrapper"></main>
            </body></html>
            """,
            "campaign",
        )
        soup = BeautifulSoup(rendered, "html.parser")
        iframes = soup.select("iframe.iframe-visible")
        permissions = iframes[0].get("allow", "").split("; ")

        self.assertEqual(len(iframes), 1)
        self.assertIn("camera", permissions)
        self.assertIn("clipboard-read", permissions)
        self.assertIn("clipboard-write", permissions)
