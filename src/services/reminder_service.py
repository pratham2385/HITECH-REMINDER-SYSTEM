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
    now_utc: datetime | None = None,
) -> list[Activity]:
    """Return due activities as scheduler/email domain objects."""

    return [
        activity_record_to_domain(record)
        for record in get_due_activity_records(session, logger, now_utc)
    ]


def build_preview_content(
    session: Session,
    logger: logging.Logger,
    now_utc: datetime | None = None,
) -> EmailContent | None:
    """Build today's reminder email content without sending it."""

    due_activities = get_due_domain_activities(session, logger, now_utc)
    if not due_activities:
        return None
    return EmailTemplate.build("Preview Mode (Assigned Users)", due_activities, date.today())


def send_daily_reminders(
    session: Session,
    settings: Settings,
    logger: logging.Logger,
    now_utc: datetime | None = None,
) -> ReminderDispatchResult:
    """Send today's email and WhatsApp reminders from database activities."""

    from datetime import datetime
    now = now_utc or datetime.utcnow()
    active_settings = effective_settings(session, settings)
    
    # We fetch records directly so we can mutate next_run_at and last_run_at
    records = get_due_activity_records(session, logger, now)
    if not records:
        return ReminderDispatchResult(
            activity_count=0,
            email_result=None,
            whatsapp_result=None,
            message="No activities due right now.",
        )
        
    due_activities = [activity_record_to_domain(r) for r in records]

    from src.db.models import ReminderRun, User

    reminder_run = ReminderRun(
        run_date=now.isoformat(),
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

    # All active and verified users should receive reminders for unassigned activities (global)
    active_users = session.query(User).filter(User.is_active == True, User.email_verified == True).all()
    verified_emails = {u.email for u in active_users if u.email}
    global_recipients = list(verified_emails)

    all_email_success = True
    messages = []
    
    from jinja2 import Template
    from src.models import EmailContent

    for act_domain in due_activities:
        # Find the matching DB record to access custom templates
        record = next((r for r in records if r.id == act_domain.row_number), None)
        
        if act_domain.assigned_user_email:
            if act_domain.assigned_user_email in verified_emails:
                recipients = [act_domain.assigned_user_email]
            else:
                logger.info(
                    "Activity: %s | Assigned User: %s | Result: Skipped (User not verified or inactive)",
                    act_domain.activity,
                    act_domain.assigned_user_email
                )
                continue
        else:
            recipients = global_recipients
            
        # Default templates
        subject = f"Reminder: {act_domain.activity}"
        body = f"Hello,\\n\\nThis is a reminder for the activity: {act_domain.activity}.\\nDue date: {now.date()}\\n\\nRegards,\\nHITECH Reminder System"
        
        # Override with custom templates if provided
        if record and record.email_subject_template:
            subject = Template(record.email_subject_template).render(
                user_name=act_domain.assigned_user_name or "User",
                user_email=act_domain.assigned_user_email or "",
                activity_name=act_domain.activity,
                frequency=act_domain.frequency,
                due_date=str(now.date()),
                current_date=str(now.date())
            )
            
        if record and record.email_body_template:
            body = Template(record.email_body_template).render(
                user_name=act_domain.assigned_user_name or "User",
                user_email=act_domain.assigned_user_email or "",
                activity_name=act_domain.activity,
                frequency=act_domain.frequency,
                due_date=str(now.date()),
                current_date=str(now.date())
            )
            # Replace newlines with <br> for HTML email
            body = body.replace("\\n", "<br>")
        else:
            # If no custom body template, we can still use the global EmailTemplate builder for a nice HTML table
            email_content = EmailTemplate.build(recipients, [act_domain], now.date())
            body = email_content.body
            subject = email_content.subject

        email_content = EmailContent(recipient=recipients, subject=subject, body=body)
        email_result = GmailEmailSender(active_settings, logger).send(email_content)
        
        logger.info(
            "Activity: %s | Assigned User Email: %s | SMTP Recipient: %s | Result: %s",
            act_domain.activity,
            act_domain.assigned_user_email,
            ", ".join(recipients) if isinstance(recipients, list) else recipients,
            "Success" if email_result.success else "Failure"
        )

        if not email_result.success:
            all_email_success = False
        messages.append(f"{act_domain.activity}: {email_result.message}")
        
        session.add(
            EmailLog(
                reminder_run_id=reminder_run.id,
                recipient=", ".join(recipients),
                subject=email_content.subject,
                success=email_result.success,
                message=email_result.message,
            )
        )
        
    reminder_run.email_status = "sent" if all_email_success else "failed"

    whatsapp_result: WhatsAppSendResult | None = None
    if active_settings.whatsapp_enabled:
        whatsapp_result = WhatsAppSender(active_settings, logger).send_activity_reminder(
            due_activities,
            now.date(),
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

    aggregated_email_result = EmailSendResult(success=all_email_success, message=" | ".join(messages))

    # Update database records with last_run_at and calculate next_run_at
    from src.scheduler.scheduler_engine import get_next_run_time
    from datetime import timedelta
    
    for record in records:
        record.last_run_at = now
        # Calculate the next run time starting from exactly 1 minute in the future
        # so it doesn't immediately match the same minute again
        next_calc_start = now + timedelta(minutes=1)
        record.next_run_at = get_next_run_time(
            frequency=record.frequency,
            timezone_str=record.timezone,
            send_time_str=record.send_time,
            day_of_week=record.day_of_week,
            day_of_month=record.day_of_month,
            month_of_year=record.month_of_year,
            year=record.year,
            quarter_months=record.quarter_months,
            date_handling_strategy=record.date_handling_strategy,
            from_time_utc=next_calc_start
        )

    reminder_run.message = "Reminder run completed."
    session.flush()
    return ReminderDispatchResult(
        activity_count=len(due_activities),
        email_result=aggregated_email_result,
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


def retry_failed_notifications(
    session: Session,
    settings: Settings,
    logger: logging.Logger,
) -> None:
    """Deprecated: The new per-minute scheduler handles retries via missed_execution_strategy."""
    logger.info("retry_failed_notifications is deprecated. The per-minute scheduler engine handles execution reliability natively.")
    pass

