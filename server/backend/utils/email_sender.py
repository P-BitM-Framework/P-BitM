# admin-backend/utils/email_sender.py

import smtplib
import ssl
import re
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple, Optional
from models import SMTPProfile, EmailTemplate, Victim
from utils.secret_storage import decrypt_secret
import logging

logger = logging.getLogger(__name__)


def sanitize_email_header(value: object) -> str:
    """Return a single-line value that is safe for an email header."""
    text = str(value or "")
    cleaned = "".join(
        " " if character in "\r\n" or ord(character) < 32 or ord(character) == 127
        else character
        for character in text
    )
    return " ".join(cleaned.split())


def create_smtp_ssl_context(ignore_cert_errors: bool) -> ssl.SSLContext:
    """Build a client TLS context, disabling verification only when requested."""
    context = ssl.create_default_context()
    if ignore_cert_errors:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def inject_tracking_pixel(html_content: str, tracking_pixel: str) -> str:
    """Place the tracking image inside the HTML document when possible."""
    if not tracking_pixel:
        return html_content

    safe_tracking_pixel = escape(tracking_pixel, quote=True)
    pixel_tag = (
        f'<img src="{safe_tracking_pixel}" alt="" width="1" height="1" '
        'style="display:block;width:1px;height:1px;border:0;opacity:0;" />'
    )
    for closing_tag in (r"</body\s*>", r"</html\s*>"):
        match = re.search(closing_tag, html_content, flags=re.IGNORECASE)
        if match:
            return (
                html_content[:match.start()]
                + pixel_tag
                + html_content[match.start():]
            )
    return html_content + pixel_tag


class EmailSender:
    """
    Email sender with persistent SMTP connection support.
    Useful for batch sending emails in campaigns.
    """

    def __init__(self, sending_profile: SMTPProfile):
        self.profile = sending_profile
        self.connection: Optional[smtplib.SMTP] = None
        self.is_connected = False

    def _ssl_context(self) -> ssl.SSLContext:
        return create_smtp_ssl_context(self.profile.ignore_cert_errors)

    def connect(self) -> Tuple[bool, str]:
        """
        Open persistent SMTP connection.

        Returns:
            (success: bool, message: str)
        """
        try:
            if self.profile.smtp_use_ssl:
                self.connection = smtplib.SMTP_SSL(
                    self.profile.smtp_host,
                    self.profile.smtp_port,
                    timeout=30,
                    context=self._ssl_context(),
                )
            else:
                self.connection = smtplib.SMTP(
                    self.profile.smtp_host,
                    self.profile.smtp_port,
                    timeout=30
                )
                if self.profile.smtp_use_tls:
                    self.connection.starttls(context=self._ssl_context())

            smtp_password = decrypt_secret(self.profile.smtp_password)
            if self.profile.smtp_username and smtp_password:
                self.connection.login(self.profile.smtp_username, smtp_password)

            self.is_connected = True
            return True, "Connected to SMTP server"

        except smtplib.SMTPAuthenticationError:
            self.disconnect()
            return False, "Authentication failed - check username/password"
        except ssl.SSLCertVerificationError:
            self.disconnect()
            return False, "TLS certificate verification failed"
        except (TimeoutError, smtplib.SMTPServerDisconnected):
            self.disconnect()
            return False, "SMTP server did not respond"
        except (OSError, smtplib.SMTPException):
            self.disconnect()
            return False, "Unable to establish the SMTP connection"
        except Exception:
            logger.exception("Unexpected SMTP connection failure")
            self.disconnect()
            return False, "Unable to establish the SMTP connection"

    def disconnect(self):
        """Close SMTP connection."""
        if self.connection:
            try:
                self.connection.quit()
            except (OSError, smtplib.SMTPException):
                try:
                    self.connection.close()
                except OSError:
                    logger.debug("Failed to close SMTP connection", exc_info=True)
            finally:
                self.connection = None
                self.is_connected = False

    def send_phishing_email(
        self,
        victim: Victim,
        template: EmailTemplate,
        campaign_url: str = "https://your-domain.com",
        entry_path: str = "continue",
        tracking_parameter: str | None = None,
    ) -> Tuple[bool, str]:
        """
        Send phishing email with tracking pixel and link.

        Args:
            victim: Victim instance with tracking_id
            template: EmailTemplate with HTML content
            campaign_url: Base URL for tracking

        Returns:
            (success: bool, error_message: str)
        """

        # Generate tracking URLs
        tracking_id = victim.tracking_id  # Usa tracking_id invece di tracking_id
        clean_url = (
            f"{campaign_url}/{entry_path}"
            if entry_path
            else campaign_url
        )
        tracking_url = (
            f"{clean_url}?{tracking_parameter}={tracking_id}"
            if tracking_parameter
            else f"{clean_url}/{tracking_id}"
        )
        tracking_pixel = f"{campaign_url}/p/{tracking_id}.png"

        # Replace template variables
        subject = self._replace_variables(
            template.subject,
            victim=victim,
            tracking_url=tracking_url,
            tracking_pixel=tracking_pixel,
            context="header",
        )

        html_content = self._replace_variables(
            template.html_content or "",
            victim=victim,
            tracking_url=tracking_url,
            tracking_pixel=tracking_pixel,
            context="html",
        )

        text_content = self._replace_variables(
            template.text_content or "",
            victim=victim,
            tracking_url=tracking_url,
            tracking_pixel=tracking_pixel,
            context="text",
        )

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        from_name = sanitize_email_header(
            getattr(self.profile, "from_name", ""),
        )
        msg['From'] = (
            f"{from_name} <{self.profile.from_email}>"
            if from_name
            else self.profile.from_email
        )
        msg['To'] = victim.email
        msg['Reply-To'] = self.profile.from_email

        # Attach text and HTML parts
        if text_content:
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(part1)

        # Keep the tracking image inside <body>. Some email clients discard
        # nodes appended after a closing </html> tag.
        html_content = inject_tracking_pixel(html_content, tracking_pixel)

        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part2)

        # Send email
        try:
            # Use persistent connection if available, otherwise create temporary one
            if self.is_connected and self.connection:
                self.connection.sendmail(
                    self.profile.from_email,
                    [victim.email],
                    msg.as_string()
                )
            else:
                # Temporary connection for single send
                self._send_with_temp_connection(msg, victim.email)

            return True, ""

        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed"
        except smtplib.SMTPRecipientsRefused:
            return False, "SMTP server rejected the recipient"
        except smtplib.SMTPException:
            return False, "SMTP server rejected the message"
        except Exception:
            logger.exception("Unexpected email delivery failure")
            return False, "Email delivery failed"

    def _send_with_temp_connection(self, msg: MIMEMultipart, recipient: str):
        """Send email with temporary connection (fallback)."""
        if self.profile.smtp_use_ssl:
            server = smtplib.SMTP_SSL(
                self.profile.smtp_host,
                self.profile.smtp_port,
                timeout=30,
                context=self._ssl_context(),
            )
        else:
            server = smtplib.SMTP(
                self.profile.smtp_host,
                self.profile.smtp_port,
                timeout=30
            )
            if self.profile.smtp_use_tls:
                server.starttls(context=self._ssl_context())

        smtp_password = decrypt_secret(self.profile.smtp_password)
        if self.profile.smtp_username and smtp_password:
            server.login(self.profile.smtp_username, smtp_password)

        server.sendmail(self.profile.from_email, [recipient], msg.as_string())
        server.quit()

    def _replace_variables(
        self,
        text: str,
        victim: Victim,
        tracking_url: str,
        tracking_pixel: str,
        context: str = "text",
    ) -> str:
        """
        Replace template variables with actual values.

        Available variables:
        - {{first_name}}
        - {{last_name}}
        - {{email}}
        - {{position}}
        - {{company}}
        - {{tracking_url}}
        - {{tracking_pixel}}
        - {{phishing_url}} (alias for tracking_url)
        """

        if not text:
            return ""

        replacements = {
            "{{first_name}}": victim.first_name or "User",
            "{{last_name}}": victim.last_name or "",
            "{{email}}": victim.email,
            "{{position}}": getattr(victim, 'position', '') or "",
            "{{company}}": victim.company or "",
            "{{tracking_url}}": tracking_url,
            "{{phishing_url}}": tracking_url,  # Alias
            "{{tracking_pixel}}": tracking_pixel,
        }

        if context == "html":
            replacements = {
                key: escape(str(value), quote=True)
                for key, value in replacements.items()
            }
        elif context == "header":
            replacements = {
                key: sanitize_email_header(value)
                for key, value in replacements.items()
            }
        elif context != "text":
            raise ValueError("Unsupported email template context")

        result = text
        for key, value in replacements.items():
            result = result.replace(key, str(value))

        return result

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test SMTP connection without keeping it open.

        Returns:
            (success: bool, message: str)
        """
        success, message = self.connect()
        if success:
            self.disconnect()
        return success, message

    def __enter__(self):
        """Context manager support."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.disconnect()
