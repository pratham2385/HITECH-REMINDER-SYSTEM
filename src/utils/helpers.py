"""Small parsing and formatting helpers."""

from __future__ import annotations

import calendar
import math
import re
from datetime import date, datetime
from typing import Any


MONTHS_BY_NAME = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def clean_string(value: Any) -> str:
    """Return a normalized string without surrounding or repeated whitespace."""

    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_frequency(value: Any) -> str:
    """Normalize a frequency value for case-insensitive comparisons."""

    return clean_string(value).casefold()


def parse_day_number(value: Any) -> int | None:
    """Extract a valid day-of-month number from an Excel cell value."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.day

    if isinstance(value, date):
        return value.day

    if isinstance(value, int):
        day = value
    elif isinstance(value, float):
        if math.isnan(value):
            return None
        day = int(value)
    else:
        text = clean_string(value)
        if not text:
            return None
        match = re.search(r"\b([1-9]|[12][0-9]|3[01])\b", text)
        if not match:
            return None
        day = int(match.group(1))

    return day if 1 <= day <= 31 else None


def is_last_day_rule(value: Any) -> bool:
    """Return whether a value means the last day of the month."""

    text = clean_string(value).casefold()
    if not text:
        return False
    return bool(
        re.search(r"\blast\s+day\b", text)
        or re.search(r"\bend\s+of\s+(the\s+)?month\b", text)
        or text in {"month end", "month-end", "last date"}
    )


def is_last_day_of_month(run_date: date) -> bool:
    """Return whether `run_date` is the final calendar day of its month."""

    return run_date.day == calendar.monthrange(run_date.year, run_date.month)[1]


def extract_month_number(value: Any) -> int | None:
    """Extract a month number from names like 'July month' or date values."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.month

    if isinstance(value, date):
        return value.month

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return None
        month = int(value)
        return month if 1 <= month <= 12 else None

    text = clean_string(value).casefold()
    if not text:
        return None

    for token in re.findall(r"[a-zA-Z]+", text):
        month_number = MONTHS_BY_NAME.get(token)
        if month_number:
            return month_number

    numeric_match = re.search(r"\b(1[0-2]|0?[1-9])\b", text)
    if numeric_match:
        return int(numeric_match.group(1))

    return None


def format_run_date(run_date: date) -> str:
    """Format a date for log and email content."""

    return run_date.strftime("%d %B %Y")
