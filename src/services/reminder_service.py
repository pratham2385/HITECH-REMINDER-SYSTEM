"""Daily reminder orchestration for email and WhatsApp."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from src.config.settings import Settings
from src.db.models import EmailLog, ReminderRun, WhatsAppLog
from src.email.email_sender import GmailEmailSender
from src.email.email_template import EmailTemplate
from src.models import Activity, EmailContent, EmailSendResult, WhatsAppSendResult
from src.services.activity_service import activity_record_to_domain, get_due_activity_records
from src.services.settings_service import effective_settings
from src.whatsapp.whatsapp_sender import WhatsAppSender


@dataclass(frozen=True, slots=True)
class ReminderDispatchResult:
    """Summary returned after one reminder dispatch attempt."""

    activity_count: int
    email_result: EmailSendResult | None
    whatsapp_result: WhatsAppSendResult | None
    message: str


def get_due_domain_activities(
    session: Session,
    logger: logging.Logger,
    run_date: date | None = None,
) -> list[Activity]:
    """Return due activities as scheduler/email domain objects."""

    effective_date = run_date or date.today()
    return [
        activity_record_to_domain(record)
        for record in get_due_activity_records(session, effective_date, logger)
    ]


def build_preview_content(
    session: Session,
    logger: logging.Logger,
    run_date: date | None = None,
) -> EmailContent | None:
    """Build today's reminder email content without sending it."""

    due_activities = get_due_domain_activities(session, logger, run_date)
    if not due_activities:
        return None
    return EmailTemplate.build(due_activities, run_date or date.today())


def send_daily_reminders(
    session: Session,
    settings: Settings,
    logger: logging.Logger,
    run_date: date | None = None,
) -> ReminderDispatchResult:
    """Send today's email and WhatsApp reminders from database activities."""

    effective_date = run_date or date.today()
    active_settings = effective_settings(session, settings)
    due_activities = get_due_domain_activities(session, logger, effective_date)

    reminder_run = ReminderRun(
        run_date=effective_date.isoformat(),
        activity_count=len(due_activities),
        email_status="not_sent",
        whatsapp_status="not_sent",
    )
    session.add(reminder_run)
    session.flush()

    if not due_activities:
        reminder_run.message = "No activities due today. No notifications sent."
        return ReminderDispatchResult(
            activity_count=0,
            email_result=None,
            whatsapp_result=None,
            message=reminder_run.message,
        )

    email_content = EmailTemplate.build(due_activities, effective_date)
    email_result = GmailEmailSender(active_settings, logger).send(email_content)
    reminder_run.email_status = "sent" if email_result.success else "failed"
    session.add(
        EmailLog(
            reminder_run_id=reminder_run.id,
            recipient=active_settings.recipient_email,
            subject=email_content.subject,
            success=email_result.success,
            message=email_result.message,
        )
    )

    whatsapp_result: WhatsAppSendResult | None = None
    if active_settings.whatsapp_enabled:
        whatsapp_result = WhatsAppSender(active_settings, logger).send_activity_reminder(
            due_activities,
            effective_date,
        )
        reminder_run.whatsapp_status = "sent" if whatsapp_result.success else "failed"
        session.add(
            WhatsAppLog(
                reminder_run_id=reminder_run.id,
                recipient=active_settings.whatsapp_recipient_number,
                template_name=active_settings.whatsapp_template_name,
                success=whatsapp_result.success,
                provider_message_id=whatsapp_result.provider_message_id,
                message=whatsapp_result.message,
            )
        )
    else:
        reminder_run.whatsapp_status = "disabled"

    reminder_run.message = "Reminder run completed."
    session.flush()
    return ReminderDispatchResult(
        activity_count=len(due_activities),
        email_result=email_result,
        whatsapp_result=whatsapp_result,
        message=reminder_run.message,
    )


def test_activity() -> list[Activity]:
    """Return a small synthetic activity list for test notifications."""

    return [Activity("Test dashboard reminder", "Daily", "", 0)]


def send_test_email(
    session: Session,
    settings: Settings,
    logger: logging.Logger,
) -> EmailSendResult:
    """Send a test email using effective dashboard settings."""

    active_settings = effective_settings(session, settings)
    content = EmailTemplate.build(test_activity(), date.today())
    result = GmailEmailSender(active_settings, logger).send(content)
    session.add(
        EmailLog(
            recipient=active_settings.recipient_email,
            subject=content.subject,
            success=result.success,
            message=f"Test email: {result.message}",
        )
    )
    session.flush()
    return result


def send_test_whatsapp(
    session: Session,
    settings: Settings,
    logger: logging.Logger,
) -> WhatsAppSendResult:
    """Send a test WhatsApp notification using effective dashboard settings."""

    active_settings = effective_settings(session, settings)
    result = WhatsAppSender(active_settings, logger).send_activity_reminder(test_activity(), date.today())
    session.add(
        WhatsAppLog(
            recipient=active_settings.whatsapp_recipient_number,
            template_name=active_settings.whatsapp_template_name,
            success=result.success,
            provider_message_id=result.provider_message_id,
            message=f"Test WhatsApp: {result.message}",
        )
    )
    session.flush()
    return result

