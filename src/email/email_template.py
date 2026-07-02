"""Email subject and body formatting."""

from __future__ import annotations

from datetime import date

from src.config.settings import APP_NAME
from src.models import Activity, EmailContent
from src.utils.helpers import format_run_date


class EmailTemplate:
    """Builds professional reminder emails."""

    @staticmethod
    def build(activities: list[Activity], run_date: date | None = None) -> EmailContent:
        """Generate subject and body for the due activities."""

        effective_date = run_date or date.today()
        subject = "Activities Scheduled for Today"

        activity_lines = "\n".join(
            f"{index}. {activity.activity}" for index, activity in enumerate(activities, start=1)
        )

        body = (
            "Dear Sir,\n\n"
            f"The following activities are scheduled for today ({format_run_date(effective_date)}):\n\n"
            f"{activity_lines}\n\n"
            "Regards,\n"
            f"{APP_NAME}"
        )

        return EmailContent(subject=subject, body=body)

