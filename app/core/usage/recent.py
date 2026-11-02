"""Share of a quota window used recently, derived from recorded quota readings.

All datetimes are naive UTC, matching the quota history tables.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

SHORT_LOOKBACK = timedelta(hours=1)
LONG_LOOKBACK = timedelta(days=1)


def recent_lookback(window: timedelta) -> timedelta:
    """The last hour for windows of a day or less (5h), the last 24 hours for longer ones (weekly)."""
    return SHORT_LOOKBACK if window <= timedelta(days=1) else LONG_LOOKBACK


@dataclass(frozen=True, slots=True)
class Reading:
    observed_at: datetime
    used_percent: float


def recent_used_percent(
    *,
    used_percent: float,
    resets_at: datetime | None,
    window: timedelta,
    baseline: Reading | None,
    now: datetime,
) -> float | None:
    """Used percent gained since the lookback began, or None when the history cannot tell.

    ``baseline`` is the latest reading at or before ``now - recent_lookback(window)``. A window that began
    inside the lookback counts its whole usage as recent; a baseline from before the current window began
    says nothing about it.
    """
    if resets_at is None:
        return None
    since = now - recent_lookback(window)
    window_start = resets_at - window
    if window_start >= since:
        return _clamp(used_percent)
    if baseline is None or baseline.observed_at < window_start:
        return None
    return _clamp(used_percent - baseline.used_percent)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)
