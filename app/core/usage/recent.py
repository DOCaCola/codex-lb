"""Share of a quota window used recently, derived from recorded quota readings.

All datetimes are naive UTC, matching the quota history tables.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum

from fastapi import Query
from pydantic import AwareDatetime

from app.core.exceptions import DashboardValidationError
from app.core.utils.time import to_utc_naive, utcnow

_SHORT_WINDOW_MAX = timedelta(days=1)
# A calendar day is at most 25 hours long, on the day daylight saving time ends.
_LONG_SINCE_MAX_AGE = timedelta(hours=25)


class ShortLookbackMinutes(IntEnum):
    """Recent-usage periods offered for windows of a day or less (5h)."""

    MINUTES_15 = 15
    MINUTES_30 = 30
    HOUR_1 = 60


class LongLookbackMinutes(IntEnum):
    """Recent-usage periods offered for longer windows (weekly)."""

    HOUR_1 = 60
    HOURS_2 = 120
    HOURS_4 = 240
    HOURS_6 = 360
    HOURS_12 = 720
    HOURS_24 = 1440


@dataclass(frozen=True, slots=True)
class RecentLookbacks:
    """How far back recent usage looks: ``short`` for windows of a day or less (5h), ``long`` for longer ones."""

    short: timedelta = timedelta(minutes=ShortLookbackMinutes.HOUR_1)
    long: timedelta = timedelta(minutes=LongLookbackMinutes.HOURS_24)

    def for_window(self, window: timedelta) -> timedelta:
        return self.short if window <= _SHORT_WINDOW_MAX else self.long

    def group[Name: str](self, windows: dict[Name, timedelta]) -> dict[timedelta, list[Name]]:
        """Window names by the lookback that applies to them."""
        groups: dict[timedelta, list[Name]] = {}
        for name, length in windows.items():
            groups.setdefault(self.for_window(length), []).append(name)
        return groups


def recent_lookbacks_query(
    recent_short_minutes: ShortLookbackMinutes = Query(ShortLookbackMinutes.HOUR_1, alias="recentShortMinutes"),
    recent_long_minutes: LongLookbackMinutes | None = Query(None, alias="recentLongMinutes"),
    recent_long_since: AwareDatetime | None = Query(None, alias="recentLongSince"),
) -> RecentLookbacks:
    """The recent-usage periods a dashboard request asks for.

    The long period is either a fixed length (``recentLongMinutes``, 24 hours when neither is given) or runs from
    ``recentLongSince``, the start of the client's day; the server does not know the client's time zone.
    """
    short = timedelta(minutes=recent_short_minutes)
    if recent_long_since is None:
        long_minutes = LongLookbackMinutes.HOURS_24 if recent_long_minutes is None else recent_long_minutes
        return RecentLookbacks(short, timedelta(minutes=long_minutes))
    if recent_long_minutes is not None:
        raise DashboardValidationError("Send either recentLongMinutes or recentLongSince, not both")
    long = utcnow() - to_utc_naive(recent_long_since)
    if not timedelta(0) < long <= _LONG_SINCE_MAX_AGE:
        raise DashboardValidationError("recentLongSince must lie within the last 25 hours")
    return RecentLookbacks(short, long)


@dataclass(frozen=True, slots=True)
class Reading:
    observed_at: datetime
    used_percent: float


def recent_used_percent(
    *,
    used_percent: float,
    resets_at: datetime | None,
    window: timedelta,
    lookback: timedelta,
    baseline: Reading | None,
    now: datetime,
) -> float | None:
    """Used percent gained since the lookback began, or None when the history cannot tell.

    ``baseline`` is the latest reading at or before ``now - lookback``. A window that began inside the lookback
    counts its whole usage as recent; a baseline from before the current window began says nothing about it.
    """
    if resets_at is None:
        return None
    since = now - lookback
    window_start = resets_at - window
    if window_start >= since:
        return _clamp(used_percent)
    if baseline is None or baseline.observed_at < window_start:
        return None
    return _clamp(used_percent - baseline.used_percent)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)
