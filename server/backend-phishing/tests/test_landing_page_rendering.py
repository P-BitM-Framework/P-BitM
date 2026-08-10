import unittest

from utils.landing_page import replace_variables


class LandingPageRenderingTests(unittest.TestCase):
    def test_recipient_variables_are_html_escaped(self):
        rendered = replace_variables(
            (
                '<p>{{first_name}}</p>'
                '<input value="{{email}}">'
                '<a href="{{target_url}}">{{company}}</a>'
            ),
            {
                "first_name": "<script>alert(1)</script>",
                "email": '" onfocus="alert(1)',
                "company": "A&B",
            },
            'https://example.test/?a=1&b="quoted"',
        )

        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&quot; onfocus=&quot;", rendered)
        self.assertIn("A&amp;B", rendered)
        self.assertIn(
            'https://example.test/?a=1&amp;b=&quot;quoted&quot;',
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
