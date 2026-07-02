"""Application entry point for the Automated Activity Reminder System."""

from __future__ import annotations

from datetime import date

from src.config.settings import load_settings
from src.email.email_sender import GmailEmailSender
from src.email.email_template import EmailTemplate
from src.excel.excel_reader import ExcelActivityReader, ExcelReaderError
from src.scheduler.schedule_checker import ScheduleChecker
from src.utils.helpers import format_run_date
from src.utils.logger import setup_logging


def run() -> int:
    """Execute one reminder run and return a process exit code."""

    settings = load_settings()
    logger = setup_logging(settings.log_dir)

    logger.info("Program Started")
    logger.info("Run date | %s", format_run_date(date.today()))

    try:
        reader = ExcelActivityReader(settings.excel_path, logger)
        activities = reader.load_activities()

        checker = ScheduleChecker(logger)
        due_activities = checker.get_due_activities(activities)

        if not due_activities:
            logger.info("No activities due today. No email sent.")
            logger.info("Program Finished")
            return 0

        email_content = EmailTemplate.build(due_activities)
        logger.info("Email Generated | activity_count=%s", len(due_activities))

        sender = GmailEmailSender(settings, logger)
        result = sender.send(email_content)

        logger.info(
            "Email status | success=%s | message=%s | activity_count=%s",
            result.success,
            result.message,
            len(due_activities),
        )
        logger.info("Program Finished")
        return 0 if result.success else 1

    except ExcelReaderError as exc:
        logger.error("Excel processing failed: %s", exc)
    except Exception:
        logger.exception("Unexpected exception occurred")

    logger.info("Program Finished")
    return 1


if __name__ == "__main__":
    raise SystemExit(run())

