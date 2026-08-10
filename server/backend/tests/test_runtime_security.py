import unittest

from utils.runtime_security import validate_runtime_security


def valid_environment():
    return {
        "ENVIRONMENT": "production",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "A-secure-initial-password-123",
        "INTERNAL_API_KEY": "i" * 32,
        "DATA_ENCRYPTION_KEY": "e" * 32,
    }


class RuntimeSecurityTests(unittest.TestCase):
    def test_valid_generated_configuration_is_accepted(self):
        validate_runtime_security(valid_environment())

    def test_missing_secret_is_rejected(self):
        environment = valid_environment()
        del environment["INTERNAL_API_KEY"]
        with self.assertRaises(RuntimeError):
            validate_runtime_security(environment)

    def test_placeholder_is_rejected(self):
        environment = valid_environment()
        environment["INTERNAL_API_KEY"] = "replace-with-a-long-random-value"
        with self.assertRaises(RuntimeError):
            validate_runtime_security(environment)

    def test_short_initial_password_is_rejected(self):
        environment = valid_environment()
        environment["ADMIN_PASSWORD"] = "short"
        with self.assertRaises(RuntimeError):
            validate_runtime_security(environment)


if __name__ == "__main__":
    unittest.main()
