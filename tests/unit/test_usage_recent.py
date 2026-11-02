from datetime import datetime, timedelta

import pytest

from app.core.usage.recent import LONG_LOOKBACK, SHORT_LOOKBACK, Reading, recent_lookback, recent_used_percent

NOW = datetime(2026, 11, 2, 12, 0, 0)
FIVE_HOURS = timedelta(hours=5)
WEEK = timedelta(days=7)


def test_lookback_is_an_hour_for_short_windows_and_a_day_for_weekly_ones():
    assert recent_lookback(FIVE_HOURS) == SHORT_LOOKBACK == timedelta(hours=1)
    assert recent_lookback(WEEK) == LONG_LOOKBACK == timedelta(days=1)


def test_recent_usage_is_the_gain_since_the_baseline():
    baseline = Reading(NOW - timedelta(minutes=70), 25.0)
    recent = recent_used_percent(
        used_percent=40.0, resets_at=NOW + timedelta(hours=3), window=FIVE_HOURS, baseline=baseline, now=NOW
    )
    assert recent == pytest.approx(15.0)


def test_a_window_that_began_inside_the_lookback_counts_all_its_usage():
    stale = Reading(NOW - timedelta(hours=2), 90.0)
    recent = recent_used_percent(
        used_percent=6.0, resets_at=NOW + timedelta(hours=4, minutes=40), window=FIVE_HOURS, baseline=stale, now=NOW
    )
    assert recent == pytest.approx(6.0)


@pytest.mark.parametrize(
    ("baseline", "resets_at"),
    [
        (None, NOW + timedelta(days=4)),
        # From before the current week began: says nothing about this window.
        (Reading(NOW - timedelta(days=3, hours=1), 80.0), NOW + timedelta(days=4)),
        (Reading(NOW - timedelta(hours=25), 30.0), None),
    ],
)
def test_recent_usage_is_unknown_without_a_reading_from_the_current_window(baseline, resets_at):
    assert recent_used_percent(used_percent=36.0, resets_at=resets_at, window=WEEK, baseline=baseline, now=NOW) is None


def test_recent_usage_is_never_negative():
    baseline = Reading(NOW - timedelta(hours=25), 40.0)
    recent = recent_used_percent(
        used_percent=38.0, resets_at=NOW + timedelta(days=4), window=WEEK, baseline=baseline, now=NOW
    )
    assert recent == 0.0
