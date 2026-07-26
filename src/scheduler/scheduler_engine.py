"""Scheduler calculation engine for determining the next execution time."""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
from typing import Optional

def get_next_run_time(
    frequency: str,
    timezone_str: str,
    send_time_str: str,
    day_of_week: Optional[str] = None,
    day_of_month: Optional[int] = None,
    month_of_year: Optional[int] = None,
    year: Optional[int] = None,
    quarter_months: Optional[str] = None,
    date_handling_strategy: str = "exact",
    from_time_utc: Optional[datetime] = None
) -> Optional[datetime]:
    """Calculate the next execution time based on schedule configuration in UTC."""
    if not frequency:
        return None
        
    frequency = frequency.strip().lower()
    
    if from_time_utc is None:
        from_time_utc = datetime.utcnow().replace(second=0, microsecond=0)
    else:
        # Strip seconds and microseconds to align with minute ticks
        from_time_utc = from_time_utc.replace(second=0, microsecond=0)
        
    try:
        tz = ZoneInfo(timezone_str or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
        
    try:
        h, m = map(int, send_time_str.split(":"))
        target_time = time(hour=h, minute=m)
    except Exception:
        target_time = time(hour=9, minute=0)
        
    # Convert "now" UTC to the target timezone to start reasoning in local time
    now_local = from_time_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    
    # We want to check days starting from today in local time
    current_date = now_local.date()
    
    # Check up to 5 years into the future to prevent infinite loops on invalid schedules
    for offset in range(365 * 5):
        candidate_date = current_date + timedelta(days=offset)
        
        # If it's today, we must ensure the target time hasn't passed yet
        if offset == 0:
            if target_time <= now_local.time():
                continue # Passed for today
                
        # Now validate the candidate_date against the frequency rules
        if _matches_schedule(
            candidate_date,
            frequency,
            day_of_week,
            day_of_month,
            month_of_year,
            year,
            quarter_months,
            date_handling_strategy
        ):
            # We found a match! Create datetime in local timezone
            naive_dt = datetime.combine(candidate_date, target_time)
            aware_dt = naive_dt.replace(tzinfo=tz)
            # Convert back to UTC
            utc_dt = aware_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            return utc_dt
            
    return None

def _matches_schedule(
    candidate: date,
    frequency: str,
    day_of_week: Optional[str],
    day_of_month: Optional[int],
    month_of_year: Optional[int],
    year: Optional[int],
    quarter_months: Optional[str],
    date_handling_strategy: str
) -> bool:
    # If a specific year is required by the schedule, it must match the candidate
    if year is not None:
        if candidate.year != year:
            return False
    if frequency == "daily":
        return True
        
    if frequency == "weekly":
        if not day_of_week:
            return False
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        try:
            target_idx = days.index(day_of_week.lower().strip())
            return candidate.weekday() == target_idx
        except ValueError:
            return False
            
    if frequency == "monthly":
        if not day_of_month:
            return False
            
        last_day = calendar.monthrange(candidate.year, candidate.month)[1]
        
        if date_handling_strategy == "last_valid_day":
            effective_target = min(day_of_month, last_day)
            return candidate.day == effective_target
        else:
            # Exact
            if day_of_month > last_day:
                return False # Never matches this month, e.g. Feb 31
            return candidate.day == day_of_month
            
    if frequency == "quarterly":
        if not day_of_month:
            return False
            
        # Default quarters: 1, 4, 7, 10
        valid_months = [1, 4, 7, 10]
        if quarter_months:
            try:
                valid_months = [int(m.strip()) for m in quarter_months.split(",")]
            except ValueError:
                pass
                
        if candidate.month not in valid_months:
            return False
            
        last_day = calendar.monthrange(candidate.year, candidate.month)[1]
        if date_handling_strategy == "last_valid_day":
            effective_target = min(day_of_month, last_day)
            return candidate.day == effective_target
        else:
            if day_of_month > last_day:
                return False
            return candidate.day == day_of_month
            
    if frequency in ("half-yearly", "half yearly"):
        if not day_of_month:
            return False
        valid_months = [1, 7]
        if quarter_months:
            try:
                valid_months = [int(m.strip()) for m in quarter_months.split(",")]
            except ValueError:
                pass
        if candidate.month not in valid_months:
            return False
            
        last_day = calendar.monthrange(candidate.year, candidate.month)[1]
        if date_handling_strategy == "last_valid_day":
            effective_target = min(day_of_month, last_day)
            return candidate.day == effective_target
        else:
            if day_of_month > last_day:
                return False
            return candidate.day == day_of_month

    if frequency == "yearly":
        if not day_of_month or not month_of_year:
            return False
            
        if candidate.month != month_of_year:
            return False
            
        last_day = calendar.monthrange(candidate.year, candidate.month)[1]
        if date_handling_strategy == "last_valid_day":
            effective_target = min(day_of_month, last_day)
            return candidate.day == effective_target
        else:
            if day_of_month > last_day:
                return False
            return candidate.day == day_of_month
            
    if frequency == "one time":
        # A one-time event normally has a specific day, month, and year.
        # But we'll just require at least day and month.
        if not day_of_month or not month_of_year:
            return False
            
        if candidate.month != month_of_year:
            return False
            
        last_day = calendar.monthrange(candidate.year, candidate.month)[1]
        if date_handling_strategy == "last_valid_day":
            effective_target = min(day_of_month, last_day)
            return candidate.day == effective_target
        else:
            if day_of_month > last_day:
                return False
            return candidate.day == day_of_month
            
    return False
