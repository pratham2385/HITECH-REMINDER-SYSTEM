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
    )


def get_due_activity_records(
    session: Session,
    run_date: date,
    logger: logging.Logger,
) -> list[ActivityRecord]:
    """Return active database activities due on `run_date`."""

    checker = ScheduleChecker(logger)
    records = (
        session.query(ActivityRecord)
        .filter(ActivityRecord.is_active.is_(True))
        .order_by(ActivityRecord.sort_order.asc(), ActivityRecord.id.asc())
        .all()
    )
    return [record for record in records if checker.is_due(activity_record_to_domain(record), run_date)]


def get_upcoming_activity_records(
    session: Session,
    start_date: date,
    logger: logging.Logger,
    days: int = 30,
    limit: int = 20,
) -> list[tuple[date, ActivityRecord]]:
    """Return upcoming activity occurrences for dashboard display."""

    upcoming: list[tuple[date, ActivityRecord]] = []
    for offset in range(days + 1):
        run_date = start_date + timedelta(days=offset)
        for record in get_due_activity_records(session, run_date, logger):
            upcoming.append((run_date, record))
            if len(upcoming) >= limit:
                return upcoming
    return upcoming

