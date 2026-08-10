import unittest

from utils.runtime_diagnostics import (
    classify_startup_failure,
    sanitize_runtime_text,
)


class RuntimeDiagnosticTests(unittest.TestCase):
    def test_redacts_common_credentials(self):
        value = (
            "{'master_token': 'secret-value', "
            "'api_key': 'another-secret', 'port': 8083}"
        )

        sanitized = sanitize_runtime_text(value)

        self.assertNotIn("secret-value", sanitized)
        self.assertNotIn("another-secret", sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_classifies_s6_pid_one_failure(self):
        self.assertEqual(
            classify_startup_failure(
                "s6-overlay-suexec: fatal: can only run as pid 1",
                100,
            ),
            "S6_INIT_NOT_PID1",
        )

    def test_classifies_oom_exit(self):
        self.assertEqual(
            classify_startup_failure("", 137),
            "OUT_OF_MEMORY",
        )


if __name__ == "__main__":
    unittest.main()
