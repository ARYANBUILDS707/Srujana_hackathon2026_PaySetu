"""Injectable clock (T1.4; ARCHITECTURE.md Section 7; ADR-012, rule A5).

- Instants are timezone-aware UTC `datetime`s; naive datetimes are rejected.
- The legal date ("today") is the Asia/Kolkata calendar date of an instant, independent of the
  server's local timezone.
- Services receive a `Clock` (FastAPI dependency `get_clock`) and pass `today` into the pure
  domain functions; tests use `FrozenClock` for determinism.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi import Request

LEGAL_TIMEZONE = ZoneInfo("Asia/Kolkata")


class Clock(Protocol):
    def now_utc(self) -> datetime:
        """Current instant, timezone-aware, in UTC."""
        ...

    def today(self) -> date:
        """Current legal date: the Asia/Kolkata calendar date (A5)."""
        ...


def require_aware(instant: datetime) -> datetime:
    """Reject naive datetimes: their meaning depends on the machine's timezone."""
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required; naive datetimes are ambiguous.")
    return instant


def legal_date(instant: datetime) -> date:
    """Asia/Kolkata calendar date of an aware instant."""
    return require_aware(instant).astimezone(LEGAL_TIMEZONE).date()


def format_utc_timestamp(instant: datetime) -> str:
    """ISO-8601 UTC with millisecond precision and a `Z` suffix (DATABASE.md `ts` type)."""
    utc = require_aware(instant).astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class SystemClock:
    """The real clock. Never reads the server's local timezone."""

    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return legal_date(self.now_utc())


class FrozenClock:
    """A deterministic clock for tests; moves only when told to."""

    def __init__(self, instant: datetime) -> None:
        self._instant = require_aware(instant).astimezone(UTC)

    def now_utc(self) -> datetime:
        return self._instant

    def today(self) -> date:
        return legal_date(self._instant)

    def set(self, instant: datetime) -> None:
        self._instant = require_aware(instant).astimezone(UTC)

    def advance(self, delta: timedelta) -> None:
        self._instant += delta


def get_clock(request: Request) -> Clock:
    """FastAPI dependency: the application's clock (`app.state.clock`)."""
    clock: Clock = request.app.state.clock
    return clock
