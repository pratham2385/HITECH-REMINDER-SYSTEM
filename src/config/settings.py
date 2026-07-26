"""Application settings and constants."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        """Fallback used before project dependencies are installed."""

        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
STATIC_DIR = PROJECT_ROOT / "src" / "web" / "static"
TEMPLATE_DIR = PROJECT_ROOT / "src" / "web" / "templates"
DEFAULT_EXCEL_PATH = DATA_DIR / "Accountant_TODO.xlsx"
DEFAULT_DATABASE_URL = "sqlite:///data/reminder_system.sqlite3"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
APP_NAME = "Automated Activity Reminder System"


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    excel_path: Path
    database_url: str
    smtp_server: str
    smtp_port: int
    email_address: str
    email_app_password: str
    recipient_email: str
    log_dir: Path
    upload_dir: Path
    secret_key: str
    dashboard_admin_username: str
    dashboard_admin_password: str
    whatsapp_enabled: bool
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_recipient_number: str
    whatsapp_template_name: str
    whatsapp_language_code: str
    whatsapp_graph_api_url: str


def _bool_env(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    """Load settings from `.env` and process environment variables."""

    load_dotenv()

    configured_excel_path = os.getenv("EXCEL_PATH", "").strip()
    excel_path = Path(configured_excel_path) if configured_excel_path else DEFAULT_EXCEL_PATH
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL
    secret_key = os.getenv("SECRET_KEY", "local-dashboard-change-me").strip()

    return Settings(
        excel_path=excel_path.expanduser(),
        database_url=database_url,
        smtp_server=os.getenv("SMTP_SERVER", SMTP_SERVER).strip() or SMTP_SERVER,
        smtp_port=int(os.getenv("SMTP_PORT", str(SMTP_PORT))),
        email_address=os.getenv("EMAIL_ADDRESS", "").strip(),
        email_app_password=os.getenv("EMAIL_APP_PASSWORD", "").strip(),
        recipient_email=os.getenv("RECIPIENT_EMAIL", "").strip(),
        log_dir=LOG_DIR,
        upload_dir=UPLOAD_DIR,
        secret_key=secret_key or "local-dashboard-change-me",
        dashboard_admin_username=os.getenv("DASHBOARD_ADMIN_USERNAME", "owner").strip() or "owner",
        dashboard_admin_password=os.getenv("DASHBOARD_ADMIN_PASSWORD", "ChangeMe@123").strip()
        or "ChangeMe@123",
        whatsapp_enabled=_bool_env("WHATSAPP_ENABLED", False),
        whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip(),
        whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip(),
        whatsapp_recipient_number=os.getenv("WHATSAPP_RECIPIENT_NUMBER", "").strip(),
        whatsapp_template_name=os.getenv("WHATSAPP_TEMPLATE_NAME", "daily_activity_reminder").strip()
        or "daily_activity_reminder",
        whatsapp_language_code=os.getenv("WHATSAPP_LANGUAGE_CODE", "en_US").strip() or "en_US",
        whatsapp_graph_api_url=os.getenv("WHATSAPP_GRAPH_API_URL", "https://graph.facebook.com/v20.0").strip()
        or "https://graph.facebook.com/v20.0",
    )
