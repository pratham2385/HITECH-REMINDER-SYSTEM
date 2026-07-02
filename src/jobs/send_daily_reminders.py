"""CLI job for sending daily email and WhatsApp reminders."""

from __future__ import annotations

from datetime import date

from src.config.settings import load_settings
from src.db.session import db_session, init_database
from src.services.reminder_service import send_daily_reminders
from src.utils.helpers import format_run_date
from src.utils.logger import setup_logging


def run() -> int:
    """Send today's due reminders from the dashboard database."""

    settings = load_settings()
    logger = setup_logging(settings.log_dir)
    logger.info("Program Started")
    logger.info("Run date | %s", format_run_date(date.today()))

    try:
        init_database(settings)
        with db_session(settings) as session:
            result = send_daily_reminders(session, settings, logger)
            logger.info(
                "Reminder job finished | activity_count=%s | message=%s",
                result.activity_count,
                result.message,
            )
            email_failed = result.email_result is not None and not result.email_result.success
            whatsapp_failed = result.whatsapp_result is not None and not result.whatsapp_result.success
            return 1 if email_failed or whatsapp_failed else 0
    except Exception:
        logger.exception("Unexpected exception occurred")
        return 1
    finally:
        logger.info("Program Finished")


if __name__ == "__main__":
    raise SystemExit(run())

