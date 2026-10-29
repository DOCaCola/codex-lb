from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import AntigravityAccount, AntigravityQuotaHistory, ModelSource
from app.modules.antigravity.schemas import AccountState, MetadataState, QuotaBucket, Subscription, Tier
from app.modules.dashboard.antigravity_pace import build_antigravity_weekly_pace

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 29, 12, 0, 0)
RESET = NOW + timedelta(days=3)
PLAN_TIERS = {"pro": "g1-pro-tier", "ultra_5x": "g1-ultra-lite-tier", "free": None}


def _account(
    source_id: str,
    plan: str,
    weekly: dict[str, float],
    *,
    enabled: bool = True,
    polled_ago: timedelta = timedelta(minutes=2),
    poll_error: str | None = None,
    reset: datetime = RESET,
) -> AntigravityAccount:
    tier = PLAN_TIERS[plan]
    state = AccountState(
        subscription=Subscription(
            current_tier=Tier(id="free-tier" if tier is None else "standard-tier"),
            paid_tier=Tier(id=tier) if tier else None,
            observed_at=NOW.replace(tzinfo=UTC),
        ),
        quota=[
            QuotaBucket(
                family=family,
                window="weekly",
                remaining_fraction=1 - used / 100,
                resets_at=reset.replace(tzinfo=UTC),
            )
            for family, used in weekly.items()
        ],
        metadata={"quota": MetadataState(updated_at=(NOW - polled_ago).replace(tzinfo=UTC), error=poll_error)},
    )
    return AntigravityAccount(
        source_id=source_id,
        state_json=state.model_dump_json(),
        source=ModelSource(id=source_id, name=source_id, is_enabled=enabled),
    )


def _build(accounts, history=None):
    return build_antigravity_weekly_pace(
        accounts=accounts,
        weekly_history=history or {},
        now=NOW,
        working_days=None,
        smoothing_window_minutes=30,
    )


def test_each_family_is_paced_separately_in_pro_units() -> None:
    paces = _build(
        [
            _account("ultra", "ultra_5x", {"gemini": 40, "argon": 20, "claude": 50}),
            # Argon is Ultra-only, so the Pro account joins only two pools.
            _account("pro", "pro", {"gemini": 60, "claude": 10}),
            _account("free", "free", {"gemini": 75}),
        ]
    )

    by_family = {pace.family: pace.pace for pace in paces}
    assert [pace.family for pace in paces] == ["gemini", "argon", "claude"]
    assert by_family["gemini"].unit == "pro_units"
    # The free plan has no published multiple and is not pooled.
    assert by_family["gemini"].account_count == 2
    assert by_family["gemini"].total_full_credits == pytest.approx(6.0)
    assert by_family["gemini"].headroom_credits == pytest.approx(5 * 0.6 + 0.4)
    assert by_family["argon"].account_count == 1
    assert by_family["argon"].total_full_credits == pytest.approx(5.0)
    assert by_family["claude"].headroom_credits == pytest.approx(5 * 0.5 + 0.9)


def test_paused_accounts_are_inactive_and_failed_or_missed_polls_are_stale() -> None:
    paces = _build(
        [
            _account("fresh", "pro", {"gemini": 10}),
            _account("paused", "pro", {"gemini": 10}, enabled=False),
            _account("missed", "pro", {"gemini": 10}, polled_ago=timedelta(minutes=16)),
            _account("failed", "pro", {"gemini": 10}, poll_error="quota: unavailable"),
            # A passed deadline means the window already reset; its old reading is not evidence.
            _account("expired", "pro", {"gemini": 90}, reset=NOW - timedelta(minutes=5)),
        ]
    )

    assert len(paces) == 1
    pace = paces[0].pace
    assert pace.account_count == 1
    assert pace.inactive_account_count == 1
    assert pace.stale_account_count == 2


def test_families_without_a_pooled_weekly_window_are_absent() -> None:
    assert _build([_account("free", "free", {"gemini": 10})]) == []


def test_burn_follows_the_family_history_only() -> None:
    def rows(family: str, start: float):
        return [
            AntigravityQuotaHistory(
                source_id="ultra",
                family=family,
                window="weekly",
                observed_at=NOW - timedelta(minutes=20 * step),
                used_percent=start - step,
                resets_at=RESET,
            )
            for step in reversed(range(9))
        ]

    paces = _build(
        [_account("ultra", "ultra_5x", {"gemini": 20, "claude": 20})],
        {("ultra", "gemini"): rows("gemini", 20)},
    )

    by_family = {pace.family: pace.pace for pace in paces}
    # +1 point every 20 minutes on a 5-unit window is 0.15 Pro units per hour.
    assert by_family["gemini"].burn_rate_recent_credits_per_hour == pytest.approx(0.15)
    assert by_family["claude"].burn_rate_recent_credits_per_hour is None
