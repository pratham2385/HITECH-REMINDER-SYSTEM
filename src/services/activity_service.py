"""Activity query helpers."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from src.db.models import ActivityRecord
from src.models import Activity
from src.scheduler.schedule_checker import ScheduleChecker


def activity_record_to_domain(record: ActivityRecord) -> Activity:
    """Convert a database activity row into the scheduler domain model."""

    return Activity(
        activity=record.activity,
        frequency=record.frequency,
        date_value=record.date_value,
        row_number=record.id,
        assigned_user_id=record.assigned_user.id if record.assigned_user else None,
        assigned_user_email=record.assigned_user.email if record.assigned_user else None,
        assigned_user_name=record.assigned_user.display_name if record.assigned_user else None,
    )


def get_due_activity_records(
    session: Session,
    logger: logging.Logger,
    now_utc: datetime | None = None
) -> list[ActivityRecord]:
    """Return active database activities whose next_run_at is due."""
    from datetime import datetime
    
    now = now_utc or datetime.utcnow()
    records = (
        session.query(ActivityRecord)
        .filter(ActivityRecord.is_active.is_(True))
        .filter(ActivityRecord.next_run_at <= now)
        .order_by(ActivityRecord.sort_order.asc(), ActivityRecord.id.asc())
        .all()
    )
    return records


def get_upcoming_activity_records(
    session: Session,
    start_date: date,
    logger: logging.Logger,
    days: int = 30,
    limit: int = 20,
) -> list[tuple[date, ActivityRecord]]:
    """Return upcoming activity occurrences for dashboard display."""
    from datetime import datetime, timedelta
    
    end_date = datetime.utcnow() + timedelta(days=days)
    records = (
        session.query(ActivityRecord)
        .filter(ActivityRecord.is_active.is_(True))
        .filter(ActivityRecord.next_run_at != None)
        .filter(ActivityRecord.next_run_at <= end_date)
        .order_by(ActivityRecord.next_run_at.asc())
        .limit(limit)
        .all()
    )
    
    return [(r.next_run_at.date(), r) for r in records if r.next_run_at]

