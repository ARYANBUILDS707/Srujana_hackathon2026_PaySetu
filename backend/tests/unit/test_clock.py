"""T1.4: injectable clock, UTC instants and the Asia/Kolkata legal date."""

import os
import time
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.clock import (
    LEGAL_TIMEZONE,
    Clock,
    FrozenClock,
    SystemClock,
    format_utc_timestamp,
    get_clock,
    legal_date,
    require_aware,
)
from app.config import Settings
from app.domain.deemed_clock import AcceptanceState, CaseFacts, compute_clock
from app.domain.rules import RuleSet
from app.domain.types import DealType
from app.main import create_app
from tests.conftest import FROZEN_INSTANT

IST = timezone(timedelta(hours=5, minutes=30))


def test_system_clock_returns_aware_utc_now() -> None:
    now = SystemClock().now_utc()
    assert now.tzinfo is UTC
    assert abs(now - datetime.now(UTC)) < timedelta(seconds=5)


def test_system_clock_today_is_the_ist_date_of_now() -> None:
    clock = SystemClock()
    assert clock.today() in {legal_date(clock.now_utc()), legal_date(datetime.now(UTC))}


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        # 18:29:59 UTC = 23:59:59 IST: still the same date.
        (datetime(2026, 11, 1, 18, 29, 59, tzinfo=UTC), date(2026, 11, 1)),
        # 18:30 UTC = 00:00 IST next day: the legal date has already rolled over.
        (datetime(2026, 11, 1, 18, 30, tzinfo=UTC), date(2026, 11, 2)),
        # 00:15 IST on 2 Nov is still 1 Nov in UTC.
        (datetime(2026, 11, 2, 0, 15, tzinfo=IST), date(2026, 11, 2)),
        # Year end: 31 Dec 20:00 UTC is already 1 Jan in India.
        (datetime(2026, 12, 31, 20, 0, tzinfo=UTC), date(2027, 1, 1)),
    ],
)
def test_legal_date_crosses_midnight_in_ist_not_utc(instant: datetime, expected: date) -> None:
    assert legal_date(instant) == expected


def test_legal_timezone_has_a_fixed_offset_and_no_dst() -> None:
    for month in (1, 7):
        offset = datetime(2026, month, 1, tzinfo=LEGAL_TIMEZONE).utcoffset()
        assert offset == timedelta(hours=5, minutes=30)


def test_naive_datetimes_are_rejected() -> None:
    naive = datetime(2026, 11, 1, 12, 0)
    for call in (require_aware, legal_date, format_utc_timestamp, FrozenClock):
        with pytest.raises(ValueError, match="timezone-aware"):
            call(naive)
    with pytest.raises(ValueError):
        FrozenClock(FROZEN_INSTANT).set(naive)


def test_format_utc_timestamp_matches_the_database_format() -> None:
    instant = datetime(2026, 11, 1, 16, 2, 11, 123456, tzinfo=IST)
    assert format_utc_timestamp(instant) == "2026-11-01T10:32:11.123Z"
    assert format_utc_timestamp(datetime(2026, 1, 1, tzinfo=UTC)) == "2026-01-01T00:00:00.000Z"


def test_frozen_clock_is_deterministic_and_normalised_to_utc(frozen_clock: FrozenClock) -> None:
    assert frozen_clock.now_utc() == frozen_clock.now_utc() == FROZEN_INSTANT
    assert frozen_clock.today() == date(2026, 11, 1)
    clock = FrozenClock(datetime(2026, 11, 2, 0, 15, tzinfo=IST))
    assert clock.now_utc().tzinfo is UTC and clock.now_utc().day == 1
    assert clock.today() == date(2026, 11, 2)


def test_frozen_clock_moves_only_when_told(frozen_clock: FrozenClock) -> None:
    frozen_clock.advance(timedelta(hours=8))  # 18:30 UTC = midnight IST
    assert frozen_clock.today() == date(2026, 11, 2)
    frozen_clock.set(datetime(2028, 2, 29, 12, tzinfo=UTC))
    assert frozen_clock.today() == date(2028, 2, 29)


def test_result_does_not_depend_on_the_machines_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset is unavailable on this platform")
    instant = datetime(2026, 11, 1, 18, 30, tzinfo=UTC)
    results = set()
    for zone in ("UTC", "America/Los_Angeles", "Pacific/Kiritimati"):
        monkeypatch.setenv("TZ", zone)
        time.tzset()
        results.add((legal_date(instant), FrozenClock(instant).today()))
    monkeypatch.delenv("TZ", raising=False)
    time.tzset()
    assert results == {(date(2026, 11, 2), date(2026, 11, 2))}
    assert "TZ" not in os.environ


def test_domain_receives_today_from_the_clock(rule_set: RuleSet) -> None:
    clock = FrozenClock(datetime(2026, 11, 16, 18, 29, tzinfo=UTC))  # 23:59 IST, Day 15
    facts = CaseFacts(date(2026, 11, 1), DealType.VERBAL)
    assert (
        compute_clock(facts, clock.today(), rule_set).acceptance_state
        is AcceptanceState.WINDOW_OPEN
    )
    clock.advance(timedelta(minutes=1))  # 00:00 IST, Day 16
    assert (
        compute_clock(facts, clock.today(), rule_set).acceptance_state is AcceptanceState.ACCEPTED
    )


def test_app_uses_system_clock_by_default(settings: Settings) -> None:
    assert isinstance(create_app(settings).state.clock, SystemClock)


def test_clock_dependency_injects_the_apps_clock(
    settings: Settings, frozen_clock: FrozenClock
) -> None:
    app = create_app(settings, clock=frozen_clock)

    @app.get("/probe/today")
    def today(clock: Clock = Depends(get_clock)) -> dict[str, str]:  # noqa: B008
        return {"today": clock.today().isoformat(), "now": format_utc_timestamp(clock.now_utc())}

    with TestClient(app) as client:
        assert client.get("/probe/today").json() == {
            "today": "2026-11-01",
            "now": "2026-11-01T10:30:00.000Z",
        }
        frozen_clock.advance(timedelta(hours=8))
        assert client.get("/probe/today").json()["today"] == "2026-11-02"
