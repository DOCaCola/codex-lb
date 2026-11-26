"""Monthly API credit cycles."""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta


def _renewal(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, min(day, calendar.monthrange(year, month)[1]))


def credit_cycle(renews_on: int, now: datetime) -> tuple[datetime, datetime]:
    """The cycle containing ``now`` (naive UTC); a renewal day past the month's end falls on its last day."""
    this_month = _renewal(now.year, now.month, renews_on)
    if now >= this_month:
        start = this_month
        year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
        return start, _renewal(year, month, renews_on)
    year, month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
    return _renewal(year, month, renews_on), this_month


BILLING_EXHAUSTION_FALLBACK = timedelta(hours=6)
