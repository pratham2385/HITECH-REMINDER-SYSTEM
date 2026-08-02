"""Helpers for dashboard-editable notification settings."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy.orm import Session

from src.config.settings import Settings
from src.db.models import NotificationSetting


SECRET_KEYS = {"EMAIL_APP_PASSWORD"}


def get_setting(session: Session, key: str, default: str = "") -> str:
    """Return a setting value stored in the database."""

    row = session.query(NotificationSetting).filter(NotificationSetting.key == key).first()
    return row.value if row else default


def set_setting(session: Session, key: str, value: str, is_secret: bool | None = None) -> None:
    """Create or update one setting value."""

    row = session.query(NotificationSetting).filter(NotificationSetting.key == key).first()
    if row is None:
        row = NotificationSetting(key=key, value=value, is_secret=is_secret if is_secret is not None else key in SECRET_KEYS)
        session.add(row)
        return

    row.value = value
    if is_secret is not None:
        row.is_secret = is_secret


def _setting_or_env(session: Session, key: str, env_value: str) -> str:
    value = get_setting(session, key, "")
    return value if value != "" else env_value


def _bool_value(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def effective_settings(session: Session, base_settings: Settings) -> Settings:
    """Return settings with database overrides applied."""

    return replace(
        base_settings,
        email_address=_setting_or_env(session, "EMAIL_ADDRESS", base_settings.email_address),
        email_app_password=_setting_or_env(session, "EMAIL_APP_PASSWORD", base_settings.email_app_password),
        recipient_email=_setting_or_env(session, "RECIPIENT_EMAIL", base_settings.recipient_email),
    )


def masked(value: str) -> str:
    """Return a compact masked representation of a secret value."""

    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}{'*' * max(len(value) - 4, 4)}{value[-2:]}"

