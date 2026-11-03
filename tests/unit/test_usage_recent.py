from datetime import datetime, timedelta

import pytest

from app.core.usage.recent import Reading, RecentLookbacks, recent_used_percent

NOW = datetime(2026, 11, 2, 12, 0, 0)
FIVE_HOURS = timedelta(hours=5)
WEEK = timedelta(days=7)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def test_default_lookback_is_an_hour_for_short_windows_and_a_day_for_weekly_ones():
    assert RecentLookbacks().for_window(FIVE_HOURS) == HOUR
    assert RecentLookbacks().for_window(WEEK) == DAY


def test_chosen_lookbacks_apply_by_window_length_and_group_window_names():
    lookbacks = RecentLookbacks(short=timedelta(minutes=15), long=timedelta(hours=6))
    assert lookbacks.for_window(FIVE_HOURS) == timedelta(minutes=15)
    assert lookbacks.for_window(WEEK) == timedelta(hours=6)
    windows = {"five_hour": FIVE_HOURS, "seven_day": WEEK, "seven_day_opus": WEEK}
    assert lookbacks.group(windows) == {
        timedelta(minutes=15): ["five_hour"],
        timedelta(hours=6): ["seven_day", "seven_day_opus"],
    }
    # Equal lookbacks share one group, so one baseline query covers both windows.
    assert RecentLookbacks(short=HOUR, long=HOUR).group(windows) == {HOUR: ["five_hour", "seven_day", "seven_day_opus"]}


def test_recent_usage_is_the_gain_since_the_baseline():
    baseline = Reading(NOW - timedelta(minutes=70), 25.0)
    recent = recent_used_percent(
        used_percent=40.0,
        resets_at=NOW + timedelta(hours=3),
        window=FIVE_HOURS,
        lookback=HOUR,
        baseline=baseline,
        now=NOW,
    )
    assert recent == pytest.approx(15.0)


def test_a_window_that_began_inside_the_lookback_counts_all_its_usage():
    stale = Reading(NOW - timedelta(hours=2), 90.0)
    recent = recent_used_percent(
        used_percent=6.0,
        resets_at=NOW + timedelta(hours=4, minutes=40),
        window=FIVE_HOURS,
        lookback=HOUR,
        baseline=stale,
        now=NOW,
    )
    assert recent == pytest.approx(6.0)


def test_a_window_that_began_before_a_short_lookback_needs_a_baseline():
    # The window began 20 minutes ago: inside an hour, but not inside 15 minutes.
    recent = recent_used_percent(
        used_percent=6.0,
        resets_at=NOW + timedelta(hours=4, minutes=40),
        window=FIVE_HOURS,
        lookback=timedelta(minutes=15),
        baseline=Reading(NOW - timedelta(minutes=16), 4.5),
        now=NOW,
    )
    assert recent == pytest.approx(1.5)


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
    recent = recent_used_percent(
        used_percent=36.0, resets_at=resets_at, window=WEEK, lookback=DAY, baseline=baseline, now=NOW
    )
    assert recent is None


def test_recent_usage_is_never_negative():
    baseline = Reading(NOW - timedelta(hours=25), 40.0)
    recent = recent_used_percent(
        used_percent=38.0, resets_at=NOW + timedelta(days=4), window=WEEK, lookback=DAY, baseline=baseline, now=NOW
    )
    assert recent == 0.0
