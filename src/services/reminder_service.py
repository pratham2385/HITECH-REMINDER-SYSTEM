"""Daily reminder orchestration for email and WhatsApp."""

from __future__ import annotations

import logging
from collections import defaultdict
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
    return EmailTemplate.build("preview@example.com", due_activities, run_date or date.today())


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

    # Group activities by Assignee
    email_groups: dict[str, list[Activity]] = defaultdict(list)
    whatsapp_groups: dict[str, list[Activity]] = defaultdict(list)

    for act in due_activities:
        if act.email_enabled:
            email = act.assignee_email or active_settings.recipient_email
            email_groups[email].append(act)
        
        if act.whatsapp_enabled and active_settings.whatsapp_enabled:
            phone = act.assignee_phone or active_settings.whatsapp_recipient_number
            whatsapp_groups[phone].append(act)

    # Dispatch Emails
    overall_email_success = True
    email_messages = []
    
    for email, acts in email_groups.items():
        recipients = [r.strip() for r in email.split(",") if r.strip()]
        if not recipients:
            continue
        
        email_content = EmailTemplate.build(recipients, acts, effective_date)
        email_result = GmailEmailSender(active_settings, logger).send(email_content)
        
        if not email_result.success:
            overall_email_success = False
            
        email_messages.append(email_result.message)
        session.add(
            EmailLog(
                reminder_run_id=reminder_run.id,
                recipient=", ".join(recipients),
                subject=email_content.subject,
                success=email_result.success,
                message=email_result.message,
            )
        )

    if email_groups:
        reminder_run.email_status = "sent" if overall_email_success else "failed"
    else:
        reminder_run.email_status = "not_sent"

    # Dispatch WhatsApp
    overall_whatsapp_success = True
    whatsapp_messages = []
    last_whatsapp_msg_id = None
    
    if active_settings.whatsapp_enabled and whatsapp_groups:
        for phone, acts in whatsapp_groups.items():
            wa_result = WhatsAppSender(active_settings, logger).send_activity_reminder(
                acts,
                effective_date,
                phone
            )
            if not wa_result.success:
                overall_whatsapp_success = False
            
            if wa_result.provider_message_id:
                last_whatsapp_msg_id = wa_result.provider_message_id
                
            whatsapp_messages.append(wa_result.message)
            session.add(
                WhatsAppLog(
                    reminder_run_id=reminder_run.id,
                    recipient=phone,
                    template_name=active_settings.whatsapp_template_name,
                    success=wa_result.success,
                    provider_message_id=wa_result.provider_message_id,
                    message=wa_result.message,
                )
            )
        reminder_run.whatsapp_status = "sent" if overall_whatsapp_success else "failed"
    else:
        reminder_run.whatsapp_status = "disabled"

    reminder_run.message = "Reminder run completed."
    session.flush()
    
    # Return a combined result for legacy callers
    combined_email_result = EmailSendResult(overall_email_success, ", ".join(email_messages)) if email_messages else None
    combined_wa_result = WhatsAppSendResult(overall_whatsapp_success, ", ".join(whatsapp_messages), last_whatsapp_msg_id) if whatsapp_messages else None
    
    return ReminderDispatchResult(
        activity_count=len(due_activities),
        email_result=combined_email_result,
        whatsapp_result=combined_wa_result,
        message=reminder_run.message,
    )


def test_activity() -> list[Activity]:
    """Return a small synthetic activity list for test notifications."""
    return [Activity("Test dashboard reminder", "Daily", "", 0, email_enabled=True, whatsapp_enabled=True)]


def send_test_email(
    session: Session,
    settings: Settings,
    logger: logging.Logger,
) -> EmailSendResult:
    """Send a test email using effective dashboard settings."""

    active_settings = effective_settings(session, settings)
    content = EmailTemplate.build(active_settings.recipient_email, test_activity(), date.today())
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
    result = WhatsAppSender(active_settings, logger).send_activity_reminder(test_activity(), date.today(), active_settings.whatsapp_recipient_number)
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
    """Check if today's reminders failed or haven't been sent, and dispatch them."""
    from src.db.models import ReminderRun
    from sqlalchemy import and_
    
    today_iso = date.today().isoformat()
    # Check if a completely successful run already exists today
    successful_run = session.query(ReminderRun).filter(
        and_(
            ReminderRun.run_date == today_iso,
            ReminderRun.email_status == "sent",
            ReminderRun.whatsapp_status.in_(["sent", "disabled"])
        )
    ).first()
    
    if not successful_run:
        logger.info("No completely successful reminder run found for today. Attempting to dispatch/retry.")
        send_daily_reminders(session, settings, logger)
    else:
        logger.info("Reminders for today were already completely successfully sent.")
