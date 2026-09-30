from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import ClaudeQuotaHistory
from app.modules.model_sources.trends import weekly_plan

pytestmark = pytest.mark.unit
START = datetime(2026, 9, 30, tzinfo=UTC)


def sample(at, reset):
    return ClaudeQuotaHistory(
        source_id="claude-a",
        window="seven_day",
        observed_at=at.replace(tzinfo=None),
        resets_at=reset.replace(tzinfo=None) if reset else None,
        used_percent=25,
    )


def plan(rows, *, hours=4):
    return weekly_plan(rows, start=int(START.timestamp()), end=(START + timedelta(hours=hours)).timestamp())


def test_weekly_plan_begins_at_observation_not_earlier_bucket():
    observed = START + timedelta(minutes=30)
    points = plan([sample(observed, observed + timedelta(days=7))])
    assert points[0].v is None
    assert next(p.v for p in points if p.t == observed) == 100
    assert next(p.v for p in points if p.t == START + timedelta(hours=1)) == round(100 * 167.5 / 168, 2)


def test_missing_or_expired_deadlines_never_fabricate_a_plan():
    assert plan([sample(START, None)]) == []
    assert plan([sample(START, START - timedelta(hours=1))]) == []


def test_expiry_stops_guideline_without_inventing_a_new_cycle():
    reset = START + timedelta(minutes=90)
    points = plan([sample(START, reset)])
    assert next(p.v for p in points if p.t == reset) == 0
    assert all(p.v is None for p in points if p.t > reset)


@pytest.mark.parametrize("new_deadline", [None, START + timedelta(days=7)])
def test_changed_or_removed_deadline_breaks_the_line_inside_an_hour(new_deadline):
    changed = START + timedelta(minutes=45)
    points = plan([sample(START, START + timedelta(days=1)), sample(changed, new_deadline)])
    assert next(p.v for p in points if p.t == changed - timedelta(milliseconds=1)) is None
    value = next(p.v for p in points if p.t == changed)
    assert value == (None if new_deadline is None else round(100 * (168 - 0.75) / 168, 2))


def test_api_header_subsecond_precision_does_not_create_false_reset_cycles():
    reset = START + timedelta(days=7)
    rows = [sample(START, reset), sample(START + timedelta(minutes=30), reset - timedelta(microseconds=100))]
    assert all(point.v is not None for point in plan(rows))
    assert all(point.t.minute == 0 for point in plan(rows))


def test_old_unknown_rows_do_not_inherit_the_new_deadline():
    known = START + timedelta(hours=2)
    points = plan([sample(START, None), sample(known, known + timedelta(days=7))])
    assert all(p.v is None for p in points if p.t < known)
    assert next(p.v for p in points if p.t == known) == 100
