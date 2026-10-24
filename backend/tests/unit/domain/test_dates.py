from datetime import date

import pytest

from app.domain.dates import add_months, add_years_feb28


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),  # leap year
        (date(2026, 1, 31), 2, date(2026, 3, 31)),  # anchored on the start, no drift
        (date(2026, 11, 17), 2, date(2027, 1, 17)),  # year boundary
        (date(2026, 12, 31), 0, date(2026, 12, 31)),
        (date(2026, 5, 15), 24, date(2028, 5, 15)),
    ],
)
def test_add_months(start: date, months: int, expected: date) -> None:
    assert add_months(start, months) == expected


@pytest.mark.parametrize(
    ("start", "years", "expected"),
    [
        (date(2028, 2, 29), 3, date(2031, 2, 28)),
        (date(2028, 2, 29), 4, date(2032, 2, 29)),
        (date(2026, 11, 17), 3, date(2029, 11, 17)),
    ],
)
def test_add_years_feb28(start: date, years: int, expected: date) -> None:
    assert add_years_feb28(start, years) == expected


def test_negative_offsets_are_rejected() -> None:
    with pytest.raises(ValueError):
        add_months(date(2026, 1, 1), -1)
    with pytest.raises(ValueError):
        add_years_feb28(date(2026, 1, 1), -1)
