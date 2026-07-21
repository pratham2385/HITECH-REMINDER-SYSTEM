"""Authentication and user management services."""

import re
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.db.models import User, PasswordResetToken, EmailVerificationToken, LoginHistory
from src.security import hash_password, verify_password
from src.config.settings import Settings
from src.email.email_sender import GmailEmailSender
from src.models import EmailContent
import logging

logger = logging.getLogger(__name__)

class AuthService:
    """Business logic for authentication."""

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password strength (length, letters, numbers)."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Za-z]", password):
            return False, "Password must contain at least one letter."
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number."
        return True, ""

    @staticmethod
    def generate_secure_token() -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def is_account_locked(db: Session, user_id: int) -> bool:
        """Check if an account is locked due to too many failed attempts (5 in last 15 mins)."""
        fifteen_mins_ago = datetime.utcnow() - timedelta(minutes=15)
        recent_failures = (
            db.query(LoginHistory)
            .filter(
                LoginHistory.user_id == user_id,
                LoginHistory.status == "failed",
                LoginHistory.created_at >= fifteen_mins_ago
            )
            .count()
        )
        return recent_failures >= 5

    @staticmethod
    def record_login_attempt(db: Session, user_id: int | None, ip_address: str, user_agent: str, status: str):
        """Record login attempt for auditing and rate limiting."""
        db.add(
            LoginHistory(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status
            )
        )
        db.commit()

    @staticmethod
    def create_email_verification_token(db: Session, user: User) -> EmailVerificationToken:
        token_str = AuthService.generate_secure_token()
        token = EmailVerificationToken(
            user_id=user.id,
            token=token_str,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db.add(token)
        db.commit()
        return token

    @staticmethod
    def send_verification_email(settings: Settings, user: User, token: EmailVerificationToken, base_url: str):
        """Send verification email to the user."""
        verify_url = f"{base_url}/verify-email?token={token.token}"
        html_body = f"""
        <html>
        <body>
            <h2>Welcome, {user.display_name}!</h2>
            <p>Please click the link below to verify your email address:</p>
            <a href="{verify_url}">Verify Email</a>
            <p>This link will expire in 24 hours.</p>
        </body>
        </html>
        """
        content = EmailContent(
            recipient=user.email,
            subject="Verify Your Email",
            body=html_body
        )
        sender = GmailEmailSender(settings, logger)
        sender.send(content)

    @staticmethod
    def create_password_reset_token(db: Session, user: User) -> PasswordResetToken:
        token_str = AuthService.generate_secure_token()
        token = PasswordResetToken(
            user_id=user.id,
            token=token_str,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        db.add(token)
        db.commit()
        return token

    @staticmethod
    def send_password_reset_email(settings: Settings, user: User, token: PasswordResetToken, base_url: str):
        """Send password reset email."""
        reset_url = f"{base_url}/reset-password?token={token.token}"
        html_body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You requested to reset your password. Click the link below to set a new password:</p>
            <a href="{reset_url}">Reset Password</a>
            <p>This link will expire in 30 minutes.</p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
        </html>
        """
        content = EmailContent(
            recipient=user.email,
            subject="Password Reset Request",
            body=html_body
        )
        sender = GmailEmailSender(settings, logger)
        sender.send(content)
