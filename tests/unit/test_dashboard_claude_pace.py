from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import ClaudeAccount, ClaudeQuotaHistory, ModelSource
from app.modules.claude.schemas import AccountState, QuotaWindow, SubscriptionMetadata, UsageSnapshot
from app.modules.dashboard.claude_pace import build_claude_weekly_pace

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 6, 12, 0, 0)
RESET = NOW + timedelta(days=3)


def _account(
    source_id: str,
    tier: str,
    used_percent: float,
    *,
    enabled: bool = True,
    observed_ago: timedelta = timedelta(minutes=1),
    reset: datetime = RESET,
) -> ClaudeAccount:
    state = AccountState(
        subscription=SubscriptionMetadata(
            rate_limit_tier=tier, source="bootstrap", observed_at=NOW.replace(tzinfo=UTC)
        ),
        usage=UsageSnapshot(
            five_hour=QuotaWindow(utilization=0, resets_at=(NOW + timedelta(hours=2)).replace(tzinfo=UTC)),
            seven_day=QuotaWindow(utilization=used_percent, resets_at=reset.replace(tzinfo=UTC)),
        ),
        usage_updated_at=(NOW - observed_ago).replace(tzinfo=UTC),
    )
    return ClaudeAccount(
        source_id=source_id,
        state_json=state.model_dump_json(),
        source=ModelSource(id=source_id, name=source_id, is_enabled=enabled),
    )


def _build(accounts: list[ClaudeAccount], history: dict[str, list[ClaudeQuotaHistory]] | None = None):
    return build_claude_weekly_pace(
        accounts=accounts,
        seven_day_history=history or {},
        now=NOW,
        working_days=None,
        smoothing_window_minutes=30,
    )


def test_claude_pace_pools_plan_windows_in_pro_units() -> None:
    pace = _build(
        [
            _account("pro", "default_claude_pro", 50),
            _account("max5", "default_claude_max_5x", 20),
            _account("max20", "default_claude_max_20x", 75),
            _account("team", "default_claude_team", 10),
        ]
    )

    assert pace is not None
    assert pace.unit == "pro_units"
    # The team plan has no stated multiplier, so it is not pooled at all.
    assert pace.account_count == 3
    assert pace.total_full_credits == pytest.approx(26.0)
    assert pace.headroom_credits == pytest.approx(0.5 + 4.0 + 5.0)
    assert pace.stale_account_count == 0
    assert pace.inactive_account_count == 0


def test_claude_pace_reports_disabled_as_inactive_and_old_observations_as_stale() -> None:
    pace = _build(
        [
            _account("fresh", "default_claude_pro", 10),
            _account("paused", "default_claude_max_5x", 10, enabled=False),
            _account("stale", "default_claude_max_5x", 10, observed_ago=timedelta(minutes=10)),
            # A deadline in the past means the window already reset; its old reading is not evidence.
            _account("expired", "default_claude_max_5x", 90, reset=NOW - timedelta(minutes=5)),
        ]
    )

    assert pace is not None
    assert pace.account_count == 1
    assert pace.inactive_account_count == 1
    assert pace.stale_account_count == 1
    assert pace.total_full_credits == pytest.approx(1.0)


def test_claude_pace_without_pooled_accounts_is_absent() -> None:
    assert _build([_account("team", "default_claude_team", 10)]) is None


def test_claude_pace_burn_survives_sub_second_reset_jitter() -> None:
    # Reported deadlines jitter by under a second on every poll; the forecast
    # must still see one window instead of restarting at each sample.
    rows = [
        ClaudeQuotaHistory(
            source_id="max5",
            window="seven_day",
            observed_at=NOW - timedelta(minutes=20 * step),
            used_percent=20 - step,
            resets_at=RESET + timedelta(milliseconds=(-1) ** step * 400),
            provenance="usage_api",
        )
        for step in reversed(range(9))
    ]

    pace = _build([_account("max5", "default_claude_max_5x", 20)], {"max5": rows})

    assert pace is not None
    # +1 point every 20 minutes on a 5-unit window is 0.15 Pro units per hour.
    assert pace.forecast_burn_rate_credits_per_hour == pytest.approx(0.15)
    assert pace.burn_rate_recent_credits_per_hour == pytest.approx(0.15)
