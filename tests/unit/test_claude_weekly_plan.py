from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import ClaudeQuotaHistory
from app.modules.model_sources.trends import weekly_plan

pytestmark = pytest.mark.unit
START = datetime(2026, 9, 30, tzinfo=UTC)
WEEK = timedelta(days=7)


def sample(at, reset):
    return ClaudeQuotaHistory(
        source_id="claude-a",
        window="seven_day",
        observed_at=at.replace(tzinfo=None),
        resets_at=reset.replace(tzinfo=None) if reset else None,
        used_percent=25,
    )


def plan(rows, *, hours=4):
    return weekly_plan(rows, start=int(START.timestamp()), end=int((START + timedelta(hours=hours)).timestamp()))


def hourly(points):
    return [(int((point.t - START).total_seconds()) // 3600, point.v) for point in points]


def remaining(hours):
    return round(100 * hours / 168, 2)


def test_plan_uses_hourly_buckets_from_first_known_deadline():
    observed = START + timedelta(hours=1, minutes=30)
    points = plan([sample(observed, observed + WEEK)])
    assert hourly(points) == [(1, 100.0), (2, remaining(167.5)), (3, remaining(166.5)), (4, remaining(165.5))]


def test_unknown_deadlines_never_fabricate_a_plan():
    assert plan([sample(START, None)]) == []
    known = START + timedelta(hours=2)
    assert [hour for hour, _ in hourly(plan([sample(START, None), sample(known, known + WEEK)]))] == [2, 3, 4]


def test_subsecond_deadline_jitter_keeps_one_continuous_line():
    reset = START + WEEK
    jitter = [timedelta(0), timedelta(milliseconds=505), timedelta(milliseconds=-400), timedelta(milliseconds=350)]
    rows = [sample(START + timedelta(minutes=20 * index), reset + offset) for index, offset in enumerate(jitter * 3)]
    assert hourly(plan(rows)) == [(hour, remaining(168 - hour)) for hour in range(5)]


def test_new_reset_cycle_jumps_and_expired_deadline_holds_at_zero():
    first = START + timedelta(hours=1)
    points = plan([sample(START, first), sample(START + timedelta(hours=3, minutes=10), first + WEEK)])
    assert hourly(points) == [(0, remaining(1)), (1, 0.0), (2, 0.0), (3, remaining(166)), (4, remaining(165))]
