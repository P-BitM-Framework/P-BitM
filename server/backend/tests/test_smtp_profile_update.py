import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from routes.sending_profiles import SMTPProfileUpdate, update_sending_profile


def existing_profile():
    profile = SimpleNamespace(
        id="smtp-1",
        name="Relay",
        smtp_host="old.example.test",
        smtp_port=587,
        smtp_username="mailer",
        smtp_password="stored-password",
        smtp_use_tls=True,
        smtp_use_ssl=False,
        ignore_cert_errors=False,
    )
    profile.to_dict = lambda: {
        "id": profile.id,
        "smtp_host": profile.smtp_host,
        "ignore_cert_errors": profile.ignore_cert_errors,
    }
    return profile


def database_returning(profile):
    database = MagicMock()
    database.query.return_value.filter_by.return_value.first.return_value = (
        profile
    )
    return database


class SMTPProfileUpdateTests(unittest.TestCase):
    @patch("routes.sending_profiles.EmailSender")
    def test_failed_connection_rolls_back_and_rejects_update(self, sender):
        profile = existing_profile()
        database = database_returning(profile)
        sender.return_value.test_connection.return_value = (
            False,
            "Authentication failed",
        )

        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                update_sending_profile(
                    profile.id,
                    SMTPProfileUpdate(smtp_host="new.example.test"),
                    db=database,
                    current_user=SimpleNamespace(username="operator"),
                )
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("were not saved", raised.exception.detail)
        database.rollback.assert_called_once()
        database.commit.assert_not_called()

    @patch("routes.sending_profiles.EmailSender")
    def test_successful_connection_is_committed_in_same_request(self, sender):
        profile = existing_profile()
        database = database_returning(profile)
        sender.return_value.test_connection.return_value = (
            True,
            "Connected to SMTP server",
        )

        result = asyncio.run(
            update_sending_profile(
                profile.id,
                SMTPProfileUpdate(
                    smtp_host="new.example.test",
                    ignore_cert_errors=True,
                ),
                db=database,
                current_user=SimpleNamespace(username="operator"),
            )
        )

        self.assertEqual(result["smtp_host"], "new.example.test")
        self.assertTrue(result["ignore_cert_errors"])
        database.commit.assert_called_once()
        database.refresh.assert_called_once_with(profile)

    def test_ignore_cert_errors_requires_an_encrypted_transport(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(
                update_sending_profile(
                    "smtp-1",
                    SMTPProfileUpdate(
                        smtp_use_tls=False,
                        smtp_use_ssl=False,
                        ignore_cert_errors=True,
                    ),
                    db=database_returning(existing_profile()),
                    current_user=SimpleNamespace(username="operator"),
                )
            )

        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
