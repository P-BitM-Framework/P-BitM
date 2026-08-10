import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from utils.email_sender import EmailSender, create_smtp_ssl_context


def profile(**overrides):
    values = {
        "smtp_host": "smtp.example.test",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "from_email": "mailer@example.test",
        "smtp_use_tls": True,
        "smtp_use_ssl": False,
        "ignore_cert_errors": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class SMTPCertificateVerificationTests(unittest.TestCase):
    def test_context_verifies_certificates_by_default(self):
        context = create_smtp_ssl_context(False)

        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_context_can_explicitly_disable_certificate_verification(self):
        context = create_smtp_ssl_context(True)

        self.assertFalse(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)

    @patch("utils.email_sender.smtplib.SMTP_SSL")
    def test_implicit_ssl_receives_secure_context(self, smtp_ssl):
        smtp_ssl.return_value = MagicMock()

        success, _message = EmailSender(
            profile(smtp_use_ssl=True, smtp_use_tls=False)
        ).connect()

        self.assertTrue(success)
        context = smtp_ssl.call_args.kwargs["context"]
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    @patch("utils.email_sender.smtplib.SMTP")
    def test_starttls_receives_opted_out_context(self, smtp):
        server = smtp.return_value = MagicMock()

        success, _message = EmailSender(
            profile(ignore_cert_errors=True)
        ).connect()

        self.assertTrue(success)
        context = server.starttls.call_args.kwargs["context"]
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)
        self.assertFalse(context.check_hostname)

    @patch("utils.email_sender.smtplib.SMTP_SSL")
    def test_temporary_ssl_connection_uses_same_policy(self, smtp_ssl):
        server = smtp_ssl.return_value = MagicMock()
        sender = EmailSender(
            profile(
                smtp_use_ssl=True,
                smtp_use_tls=False,
                ignore_cert_errors=True,
            )
        )

        sender._send_with_temp_connection(MagicMock(), "user@example.test")

        context = smtp_ssl.call_args.kwargs["context"]
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)
        server.sendmail.assert_called_once()


if __name__ == "__main__":
    unittest.main()
