from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from app.core.utils.time import naive_utc_to_epoch
from app.db.models import Account, AccountStatus
from app.modules.accounts.schemas import AccountSummary
from app.modules.dashboard.weekly_pace import (
    PRO_WEEKLY_CAPACITY_CREDITS,
    PaceAccountInput,
    build_weekly_credit_pace,
    build_weekly_pace,
)
from app.modules.usage.depletion_service import compute_depletion_for_account, reset_ewma_state

NOW = datetime(2026, 8, 17, 12, 0, 0)
NOW_MS = naive_utc_to_epoch(NOW) * 1000.0
HOUR_MS = 3_600_000.0
WEEK_MS = 7 * 24 * HOUR_MS


@dataclass(frozen=True)
class _Sample:
    recorded_at: datetime
    used_percent: float
    reset_at: int | None
    window_minutes: int | None


def _input(
    account_id: str,
    *,
    used_percent: float,
    reset_in_hours: float,
    ends_in_hours: float | None = None,
    hourly_delta: float | None = None,
) -> PaceAccountInput:
    reset_at = int(naive_utc_to_epoch(NOW + timedelta(hours=reset_in_hours)))
    history = (
        [
            _Sample(NOW - timedelta(hours=1), used_percent - hourly_delta, reset_at, 10_080),
            _Sample(NOW, used_percent, reset_at, 10_080),
        ]
        if hourly_delta is not None
        else [_Sample(NOW - timedelta(minutes=1), used_percent, reset_at, 10_080)]
    )
    return PaceAccountInput(
        account_id=account_id,
        full_units=1.0,
        remaining_units=1.0 - used_percent / 100.0,
        reset_at_ms=NOW_MS + reset_in_hours * HOUR_MS,
        window_ms=WEEK_MS,
        history=history,
        ends_at_ms=NOW_MS + ends_in_hours * HOUR_MS if ends_in_hours is not None else None,
    )


def _pace(*accounts: PaceAccountInput, trailing_demand: dict[str, float] | None = None):
    pace = build_weekly_pace(
        accounts=accounts,
        now=NOW,
        unit="pro_units",
        pro_account_units=1.0,
        stale_account_count=0,
        inactive_account_count=0,
        trailing_demand_used_percent_by_account=trailing_demand,
        working_days=None,
        smoothing_window_minutes=30,
    )
    assert pace is not None
    return pace


def test_ending_balance_is_spent_first_and_lapses_at_the_end() -> None:
    # 0.1 units/hour against 0.5 + 0.5 units: 10 hours without an end date.
    renewing = _pace(
        _input("a", used_percent=50.0, reset_in_hours=100.0, hourly_delta=10.0),
        _input("b", used_percent=50.0, reset_in_hours=100.0),
    )
    assert renewing.depletion_eta_hours == pytest.approx(10.0)

    # b ends in 2 hours: 0.2 is spent from b, its other 0.3 lapses, a's 0.5 lasts 5 more hours.
    ending = _pace(
        _input("a", used_percent=50.0, reset_in_hours=100.0, hourly_delta=10.0),
        _input("b", used_percent=50.0, reset_in_hours=100.0, ends_in_hours=2.0),
    )
    assert ending.depletion_eta_hours == pytest.approx(7.0)
    assert ending.next_relief_in_hours == pytest.approx(100.0)
    assert ending.runway_status == "runs_dry"


def test_reset_after_the_end_is_not_relief() -> None:
    pace = _pace(
        _input("ending", used_percent=100.0, reset_in_hours=48.0, ends_in_hours=24.0),
        _input("renewing", used_percent=20.0, reset_in_hours=72.0),
    )

    assert pace.next_relief_in_hours == pytest.approx(72.0)
    assert [event.at.timestamp() for event in pace.reset_events] == [pytest.approx((NOW_MS + 72 * HOUR_MS) / 1000.0)]
    assert len(pace.subscription_ends) == 1
    assert pace.subscription_ends[0].weekly_credits == pytest.approx(1.0)
    assert pace.subscription_ends[0].at.timestamp() == pytest.approx((NOW_MS + 24 * HOUR_MS) / 1000.0)


def test_schedule_spends_the_account_by_its_end() -> None:
    # Half the window has elapsed; ending 42 hours early shortens the schedule to 5.25 days.
    renewing = _pace(_input("a", used_percent=0.0, reset_in_hours=84.0))
    ending = _pace(_input("a", used_percent=0.0, reset_in_hours=84.0, ends_in_hours=42.0))

    assert renewing.scheduled_used_percent == pytest.approx(50.0)
    assert ending.scheduled_used_percent == pytest.approx(100.0 * 3.5 / 5.25)
    assert ending.scheduled_burn_rate_credits_per_hour == pytest.approx(1.0 / (5.25 * 24))


def test_pool_that_ends_before_any_reset_has_no_relief_and_runs_dry() -> None:
    # 0.02 units/hour leaves 0.26 of the 0.5 unspent when the account ends in 12 hours.
    pace = _pace(_input("a", used_percent=50.0, reset_in_hours=24.0, ends_in_hours=12.0, hourly_delta=2.0))

    assert pace.next_relief_in_hours is None
    assert pace.reset_events == []
    assert pace.depletion_eta_hours == pytest.approx(12.0)
    assert pace.projected_depletion_hours == pytest.approx(12.0)
    assert pace.runway_status == "runs_dry"


def test_add_capacity_counts_only_the_active_share_of_the_week() -> None:
    # Demand of 1.4 Pro weeks over two Pro accounts fits, unless one ends in 1.75 days.
    trailing = {"a": 100.0, "b": 40.0}
    renewing = _pace(
        _input("a", used_percent=100.0, reset_in_hours=100.0),
        _input("b", used_percent=40.0, reset_in_hours=100.0),
        trailing_demand=trailing,
    )
    ending = _pace(
        _input("a", used_percent=100.0, reset_in_hours=100.0),
        _input("b", used_percent=40.0, reset_in_hours=100.0, ends_in_hours=42.0),
        trailing_demand=trailing,
    )

    assert renewing.add_pro_accounts is None
    assert ending.add_pro_accounts == 1


def test_passed_end_is_ignored_and_the_account_projects_as_renewing() -> None:
    summaries = [
        AccountSummary(
            account_id=account_id,
            email=f"{account_id}@example.com",
            display_name=account_id,
            plan_type="pro",
            status="active",
            reset_at_secondary=NOW + timedelta(hours=24),
            window_minutes_secondary=10_080,
            capacity_credits_secondary=PRO_WEEKLY_CAPACITY_CREDITS,
            remaining_credits_secondary=PRO_WEEKLY_CAPACITY_CREDITS / 2,
        )
        for account_id in ("acc-live", "acc-ended")
    ]
    accounts = [
        Account(id="acc-live", status=AccountStatus.ACTIVE),
        Account(id="acc-ended", status=AccountStatus.ACTIVE, subscription_ends_at=NOW - timedelta(minutes=1)),
    ]
    history = {
        account_id: [_Sample(NOW - timedelta(minutes=1), 50.0, None, 10_080)]
        for account_id in ("acc-live", "acc-ended")
    }

    pace = build_weekly_credit_pace(
        accounts=accounts,
        account_summaries=summaries,
        secondary_history=history,
        now=NOW,
        usage_refresh_interval_seconds=60,
    )

    assert pace is not None
    assert pace.account_count == 2
    assert pace.inactive_account_count == 0
    assert pace.subscription_ends == []
    assert len(pace.reset_events) == 2


@dataclass(frozen=True)
class _UsageRow:
    recorded_at: datetime
    used_percent: float
    reset_at: int | None
    window_minutes: int | None


def test_depletion_horizon_stops_at_the_subscription_end() -> None:
    # A 5-hour window resetting in 2 hours: 3 hours elapsed, burning 10% an hour from 20%.
    reset_at = int(naive_utc_to_epoch(NOW + timedelta(hours=2)))
    history = [
        _UsageRow(NOW - timedelta(hours=1), 10.0, reset_at, 300),
        _UsageRow(NOW, 20.0, reset_at, 300),
    ]
    reset_ewma_state()

    renewing = compute_depletion_for_account("acc", "standard", "primary", history, now=NOW)
    ending = compute_depletion_for_account(
        "acc", "standard", "primary", history, now=NOW, ends_at=NOW + timedelta(hours=1)
    )

    assert renewing is not None and ending is not None
    assert renewing.safe_usage_percent == pytest.approx(60.0)
    assert ending.safe_usage_percent == pytest.approx(75.0)
    assert ending.risk < renewing.risk
