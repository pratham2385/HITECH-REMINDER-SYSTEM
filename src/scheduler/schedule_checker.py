"""Determine which activities are due on a given date."""

from __future__ import annotations

import logging
from datetime import date
from typing import Final

from src.models import Activity
from src.utils.helpers import (
    extract_month_number,
    extract_weekday,
    is_last_day_of_month,
    is_last_day_rule,
    normalize_frequency,
    parse_day_number,
)
import calendar


QUARTER_MONTHS: Final[set[int]] = {1, 4, 7, 10}


class ScheduleChecker:
    """Checks activity frequencies against a run date."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def get_due_activities(
        self,
        activities: list[Activity],
        run_date: date | None = None,
    ) -> list[Activity]:
        """Return activities due on `run_date`, defaulting to today."""

        effective_date = run_date or date.today()
        due_activities: list[Activity] = []

        for activity in activities:
            if self.is_due(activity, effective_date):
                due_activities.append(activity)

        self.logger.info(
            "Today's Activities Found | date=%s | activity_count=%s",
            effective_date.isoformat(),
            len(due_activities),
        )
        return due_activities

    def is_due(self, activity: Activity, run_date: date) -> bool:
        """Return whether one activity is due on `run_date`."""

        frequency = normalize_frequency(activity.frequency)

        if frequency == "daily":
            return True

        if frequency == "monthly":
            if is_last_day_rule(activity.date_value):
                return is_last_day_of_month(run_date)

            day = parse_day_number(activity.date_value)
            if day is None:
                self.logger.warning(
                    "Skipping row %s because monthly Date is invalid: %r",
                    activity.row_number,
                    activity.date_value,
                )
                return False
            
            # If the targeted day exceeds the number of days in the current month,
            # trigger on the last day of the current month instead.
            last_day_of_current_month = calendar.monthrange(run_date.year, run_date.month)[1]
            effective_trigger_day = min(day, last_day_of_current_month)
            return run_date.day == effective_trigger_day

        if frequency == "quarterly":
            day = parse_day_number(activity.date_value)
            if day is None:
                self.logger.warning(
                    "Skipping row %s because quarterly Date is invalid: %r",
                    activity.row_number,
                    activity.date_value,
                )
                return False
            return run_date.month in QUARTER_MONTHS and run_date.day == day

        if frequency == "weekly":
            weekday = extract_weekday(activity.date_value)
            if weekday is None:
                self.logger.warning(
                    "Skipping row %s because weekly Date is invalid: %r",
                    activity.row_number,
                    activity.date_value,
                )
                return False
            return run_date.weekday() == weekday

        if frequency == "bi-weekly" or frequency == "biweekly":
            weekday = extract_weekday(activity.date_value)
            if weekday is None:
                self.logger.warning(
                    "Skipping row %s because bi-weekly Date is invalid: %r",
                    activity.row_number,
                    activity.date_value,
                )
                return False
            return run_date.weekday() == weekday and run_date.isocalendar()[1] % 2 == 0

        if frequency == "yearly":
            month = extract_month_number(activity.date_value)
            if month is None:
                self.logger.warning(
                    "Skipping row %s because yearly Date is invalid: %r",
                    activity.row_number,
                    activity.date_value,
                )
                return False
            return run_date.month == month

        self.logger.warning(
            "Skipping row %s because Frequency is unsupported: %r",
            activity.row_number,
            activity.frequency,
        )
        return False
