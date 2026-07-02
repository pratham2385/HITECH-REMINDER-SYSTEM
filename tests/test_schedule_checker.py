"""Tests for activity schedule matching."""

from __future__ import annotations

import logging
import unittest
from datetime import date

from src.models import Activity
from src.scheduler.schedule_checker import ScheduleChecker


class ScheduleCheckerTests(unittest.TestCase):
    """Verify supported reminder frequencies."""

    def setUp(self) -> None:
        self.checker = ScheduleChecker(logging.getLogger("test"))

    def test_daily_activity_is_always_due(self) -> None:
        activity = Activity("A/c Payable", "Daily", None, 2)

        self.assertTrue(self.checker.is_due(activity, date(2026, 6, 26)))

    def test_monthly_activity_matches_day(self) -> None:
        activity = Activity("GST Payment", "Monthly", 20, 2)

        self.assertTrue(self.checker.is_due(activity, date(2026, 6, 20)))
        self.assertFalse(self.checker.is_due(activity, date(2026, 6, 21)))

    def test_quarterly_activity_matches_quarter_month_and_day(self) -> None:
        activity = Activity("Office Maintenance Payment", "Quarterly", 5, 2)

        self.assertTrue(self.checker.is_due(activity, date(2026, 7, 5)))
        self.assertFalse(self.checker.is_due(activity, date(2026, 8, 5)))
        self.assertFalse(self.checker.is_due(activity, date(2026, 7, 6)))

    def test_yearly_activity_matches_month_text(self) -> None:
        activity = Activity("Insurance", "Yearly", "July month", 2)

        self.assertTrue(self.checker.is_due(activity, date(2026, 7, 15)))
        self.assertFalse(self.checker.is_due(activity, date(2026, 8, 15)))

    def test_unsupported_frequency_is_not_due(self) -> None:
        activity = Activity("Unknown", "Weekly", "Friday", 2)

        self.assertFalse(self.checker.is_due(activity, date(2026, 6, 26)))


if __name__ == "__main__":
    unittest.main()

