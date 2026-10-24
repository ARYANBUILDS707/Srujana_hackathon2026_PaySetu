"""Calendar arithmetic on legal dates (Asia/Kolkata calendar dates; ADR-012, A5)."""

import calendar
from datetime import date


def add_months(start: date, months: int) -> date:
    """Add calendar months, clamping to the last day of the target month.

    Always anchor on the original start date (``add_months(start, k)``) rather than chaining
    calls, so 31 Jan + 1 month = 28/29 Feb and 31 Jan + 2 months = 31 Mar.
    """
    if months < 0:
        raise ValueError("months must be non-negative")
    index = start.month - 1 + months
    year, month = start.year + index // 12, index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def add_years_feb28(start: date, years: int) -> date:
    """Add calendar years; 29 Feb maps to 28 Feb in a non-leap target year (A11)."""
    if years < 0:
        raise ValueError("years must be non-negative")
    target = start.year + years
    if start.month == 2 and start.day == 29 and not calendar.isleap(target):
        return date(target, 2, 28)
    return start.replace(year=target)
