import pytest
from datetime import date
import logging
from src.scheduler.schedule_checker import ScheduleChecker
from src.models import Activity

@pytest.fixture
def logger():
    return logging.getLogger("test")

def test_daily_frequency(logger):
    checker = ScheduleChecker(logger)
    activity = Activity(
        row_number=1,
        module_name="Test",
        activity="Test Daily",
        frequency="Daily",
        date_value=None,
        link=None,
        remark=None
    )
    assert checker.is_due(activity, date(2026, 7, 15)) == True

def test_monthly_frequency(logger):
    checker = ScheduleChecker(logger)
    activity = Activity(
        row_number=1,
        module_name="Test",
        activity="Test Monthly",
        frequency="Monthly",
        date_value=15,
        link=None,
        remark=None
    )
    assert checker.is_due(activity, date(2026, 7, 15)) == True
    assert checker.is_due(activity, date(2026, 7, 16)) == False

def test_monthly_end_of_month(logger):
    checker = ScheduleChecker(logger)
    activity = Activity(
        row_number=1,
        module_name="Test",
        activity="Test EOM",
        frequency="Monthly",
        date_value="End of Month",
        link=None,
        remark=None
    )
    assert checker.is_due(activity, date(2026, 2, 28)) == True
    assert checker.is_due(activity, date(2026, 2, 27)) == False

def test_monthly_overflow(logger):
    checker = ScheduleChecker(logger)
    activity = Activity(
        row_number=1,
        module_name="Test",
        activity="Test Overflow",
        frequency="Monthly",
        date_value=31,
        link=None,
        remark=None
    )
    # Feb 28th should trigger for 31st target
    assert checker.is_due(activity, date(2026, 2, 28)) == True

def test_weekly_frequency(logger):
    checker = ScheduleChecker(logger)
    activity = Activity(
        row_number=1,
        module_name="Test",
        activity="Test Weekly",
        frequency="Weekly",
        date_value="Monday",
        link=None,
        remark=None
    )
    # July 20, 2026 is a Monday
    assert checker.is_due(activity, date(2026, 7, 20)) == True
    assert checker.is_due(activity, date(2026, 7, 21)) == False
