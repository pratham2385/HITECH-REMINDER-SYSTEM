"""Gmail SMTP email sender."""

from __future__ import annotations

import logging
import smtplib
import socket
from email.message import EmailMessage

from src.config.settings import Settings
from src.models import EmailContent, EmailSendResult


class GmailEmailSender:
    """Sends reminder emails through Gmail SMTP using TLS."""

    def __init__(self, settings: Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

    def send(self, content: EmailContent) -> EmailSendResult:
        """Send one email and return a success/failure result."""

        validation_error = self._validate_settings()
        if validation_error:
            self.logger.error(validation_error)
            return EmailSendResult(success=False, message=validation_error)

        message = EmailMessage()
        message["From"] = self.settings.email_address
        
        recipient = content.recipient if content.recipient else self.settings.recipient_email
        if isinstance(recipient, list):
            message["To"] = ", ".join(recipient)
        else:
            message["To"] = recipient

        message["Subject"] = content.subject
        message.set_content(content.body, subtype="html")

        try:
            with smtplib.SMTP(
                self.settings.smtp_server,
                self.settings.smtp_port,
                timeout=30,
            ) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self.settings.email_address, self.settings.email_app_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            error = "SMTP authentication failed. Check EMAIL_ADDRESS and EMAIL_APP_PASSWORD."
            self.logger.error("%s | %s", error, exc)
            return EmailSendResult(success=False, message=error)
        except (socket.gaierror, socket.timeout, TimeoutError, OSError) as exc:
            error = f"Network failure while sending email: {exc}"
            self.logger.error(error)
            return EmailSendResult(success=False, message=error)
        except smtplib.SMTPException as exc:
            error = f"SMTP failure while sending email: {exc}"
            self.logger.error(error)
            return EmailSendResult(success=False, message=error)

        success = "Email Sent Successfully"
        self.logger.info("%s | recipient=%s", success, message["To"])
        return EmailSendResult(success=True, message=success)

    def _validate_settings(self) -> str | None:
        """Return an error message when required email settings are missing."""

        missing = []
        if not self.settings.email_address:
            missing.append("EMAIL_ADDRESS")
        if not self.settings.email_app_password:
            missing.append("EMAIL_APP_PASSWORD")
        if not self.settings.recipient_email:
            missing.append("RECIPIENT_EMAIL")

        if missing:
            return f"Missing required email configuration: {', '.join(missing)}"

        return None

