"""Automated tests for scheduler timezone and calendar logic."""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from src.scheduler.scheduler_engine import get_next_run_time

def run_tests():
    print("--- Running Scheduler Tests ---")
    
    # 1. Weekly test: 21 July 2026 is a Tuesday.
    # From Time: 2026-07-20 12:00:00 UTC
    # Frequency: weekly, Day: Tuesday, Timezone: UTC, Time: 09:00
    base_time = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    next_tuesday = get_next_run_time(
        frequency="weekly",
        timezone_str="UTC",
        send_time_str="09:00",
        day_of_week="tuesday",
        from_time_utc=base_time
    )
    print(f"1. Next Tuesday 09:00 (from Jul 20): {next_tuesday} -> Expected: 2026-07-21 09:00:00")
    
    # 2. Leap year: 29 Feb 2028
    base_time = datetime(2028, 1, 1, 0, 0)
    next_leap = get_next_run_time(
        frequency="yearly",
        timezone_str="UTC",
        send_time_str="10:00",
        day_of_month=29,
        month_of_year=2,
        from_time_utc=base_time
    )
    print(f"2. Leap year Feb 29 (from 2028-01-01): {next_leap} -> Expected: 2028-02-29 10:00:00")
    
    # 3. Invalid leap year: 29 Feb 2027 (exact strategy -> None)
    base_time = datetime(2027, 1, 1, 0, 0)
    invalid_leap = get_next_run_time(
        frequency="yearly",
        timezone_str="UTC",
        send_time_str="10:00",
        day_of_month=29,
        month_of_year=2,
        date_handling_strategy="exact",
        from_time_utc=base_time
    )
    print(f"3. Non-leap year Feb 29 (exact): {invalid_leap} -> Expected: None (Or skipped for that year)")
    
    # 4. Invalid leap year (last_valid_day strategy -> Feb 28 2027)
    valid_leap_fallback = get_next_run_time(
        frequency="yearly",
        timezone_str="UTC",
        send_time_str="10:00",
        day_of_month=29,
        month_of_year=2,
        date_handling_strategy="last_valid_day",
        from_time_utc=base_time
    )
    print(f"4. Non-leap year Feb 29 (last_valid_day): {valid_leap_fallback} -> Expected: 2027-02-28 10:00:00")
    
    # 5. Monthly: 31st (last_valid_day) -> should yield Jan 31, Feb 28/29, Mar 31, Apr 30
    base_time = datetime(2027, 2, 1, 0, 0)
    next_month_end = get_next_run_time(
        frequency="monthly",
        timezone_str="UTC",
        send_time_str="11:00",
        day_of_month=31,
        date_handling_strategy="last_valid_day",
        from_time_utc=base_time
    )
    print(f"5. Monthly 31st in Feb 2027 (last_valid_day): {next_month_end} -> Expected: 2027-02-28 11:00:00")
    
    # 6. Monthly: 31st (exact) in Feb -> should skip to March 31
    next_exact_31 = get_next_run_time(
        frequency="monthly",
        timezone_str="UTC",
        send_time_str="11:00",
        day_of_month=31,
        date_handling_strategy="exact",
        from_time_utc=base_time
    )
    print(f"6. Monthly 31st in Feb 2027 (exact): {next_exact_31} -> Expected: 2027-03-31 11:00:00")
    
    # 7. Timezone test: India (Asia/Kolkata is UTC+5:30). Send at 09:30 AM IST. 
    # That is 04:00 AM UTC.
    base_time = datetime(2027, 3, 1, 0, 0)
    tz_ist = get_next_run_time(
        frequency="daily",
        timezone_str="Asia/Kolkata",
        send_time_str="09:30",
        from_time_utc=base_time
    )
    print(f"7. Timezone IST Daily 09:30 (from midnight UTC): {tz_ist} -> Expected: 2027-03-01 04:00:00")
    
    # 8. Short-duration test: 2 minutes from now
    now = datetime.utcnow().replace(second=0, microsecond=0)
    two_mins_later_local = now + timedelta(minutes=2)
    next_run_now = get_next_run_time(
        frequency="daily",
        timezone_str="UTC",
        send_time_str=two_mins_later_local.strftime("%H:%M"),
        from_time_utc=now
    )
    print(f"8. 2 mins from now {two_mins_later_local.strftime('%H:%M')}: {next_run_now} -> Expected: {two_mins_later_local}")
    
    print("--- Tests Complete ---")

if __name__ == "__main__":
    run_tests()
