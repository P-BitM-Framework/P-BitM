import string
import unittest

from pydantic import ValidationError

from routes.users import (
    GENERATED_PASSWORD_LENGTH,
    PASSWORD_SPECIAL_CHARACTERS,
    AdminPasswordReset,
    PasswordChange,
    UserCreate,
    generate_temporary_password,
)


class GeneratedUserPasswordTests(unittest.TestCase):
    def test_generated_password_has_required_length_and_character_classes(self):
        password = generate_temporary_password()

        self.assertEqual(len(password), GENERATED_PASSWORD_LENGTH)
        self.assertTrue(any(char in string.ascii_uppercase for char in password))
        self.assertTrue(any(char in string.ascii_lowercase for char in password))
        self.assertTrue(any(char in string.digits for char in password))
        self.assertTrue(any(char in PASSWORD_SPECIAL_CHARACTERS for char in password))

    def test_generated_passwords_are_not_reused(self):
        passwords = {generate_temporary_password() for _ in range(20)}

        self.assertEqual(len(passwords), 20)

    def test_password_mutation_models_only_accept_authorization_input(self):
        reset = AdminPasswordReset.model_validate({})
        change = PasswordChange.model_validate({"old_password": "current-password"})

        self.assertIsInstance(reset, AdminPasswordReset)
        self.assertEqual(change.old_password, "current-password")

        with self.assertRaises(ValidationError):
            UserCreate.model_validate({
                "username": "operator",
                "email": "operator@example.com",
                "password": "user-selected-password",
            })


if __name__ == "__main__":
    unittest.main()
