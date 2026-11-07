from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.openai.model_registry import UpstreamModel
from app.db.models import (
    Account,
    AccountStatus,
    AntigravityAccount,
    ClaudeAccount,
    ModelSource,
    OpenRouterAccount,
    UsageHistory,
)
from app.modules.antigravity.schemas import AccountState as AntigravityState
from app.modules.antigravity.schemas import MetadataState, QuotaBucket, Tier
from app.modules.antigravity.schemas import Subscription as AntigravitySubscription
from app.modules.claude.schemas import AccountState as ClaudeState
from app.modules.claude.schemas import QuotaWindow, SubscriptionMetadata, UsageSnapshot
from app.modules.dashboard.schemas import WeeklyCreditPaceResponse
from app.modules.openrouter.schemas import AccountState as OpenRouterState
from app.modules.openrouter.schemas import CreditInfo
from app.modules.proxy.usage_snapshot import antigravity_pools, chatgpt_pool, claude_pools, openrouter_pool

pytestmark = pytest.mark.unit

# Naive UTC, like stored readings.
NOW = datetime(2026, 11, 7, 11, 0, 0)
NOW_EPOCH = int(NOW.replace(tzinfo=UTC).timestamp())


def _account(account_id: str, plan_type: str, status: AccountStatus = AccountStatus.ACTIVE) -> Account:
    return Account(id=account_id, email=account_id + "@example.com", plan_type=plan_type, status=status)


def _usage(account_id: str, window: str, used: float, *, minutes: int, resets_in: timedelta) -> UsageHistory:
    return UsageHistory(
        account_id=account_id,
        window=window,
        used_percent=used,
        window_minutes=minutes,
        reset_at=NOW_EPOCH + int(resets_in.total_seconds()),
        recorded_at=NOW - timedelta(seconds=20),
    )


def _pace(**fields: object) -> WeeklyCreditPaceResponse:
    return WeeklyCreditPaceResponse.model_construct(**fields)


def test_chatgpt_pool_leaves_out_windows_only_blocked_accounts_report() -> None:
    accounts = [_account("plus", "plus"), _account("pro-spent", "pro"), _account("pro", "pro")]
    latest = {
        # The Plus account is blocked by its week, so its 5-hour window limits nothing.
        "primary": {"plus": _usage("plus", "primary", 0, minutes=300, resets_in=timedelta(hours=4))},
        "secondary": {
            "plus": _usage("plus", "secondary", 100, minutes=10080, resets_in=timedelta(days=1)),
            "pro-spent": _usage("pro-spent", "secondary", 100, minutes=10080, resets_in=timedelta(hours=9)),
            "pro": _usage("pro", "secondary", 27, minutes=10080, resets_in=timedelta(days=6)),
        },
        "monthly": {},
    }
    pace = _pace(
        runway_status="safe",
        depletion_eta_hours=None,
        next_relief_in_hours=9.0,
        headroom_credits=36_792.0,
        next_relief_credits=50_400.0,
        total_full_credits=108_360.0,
    )

    pool = chatgpt_pool(accounts=accounts, latest=latest, models=["gpt-6-sol"], pace=pace, now=NOW)

    assert pool.accounts.model_dump() == {"total": 3, "ready": 1}
    (weekly,) = pool.windows
    assert weekly.id == "weekly"
    # 36,792 of 108,360 weekly credits.
    assert weekly.left_percent == 34.0
    assert weekly.resets_at == datetime(2026, 11, 7, 20, 0, tzinfo=UTC)
    assert weekly.exhausts_at is None
    assert weekly.relief is not None
    assert weekly.relief.at == datetime(2026, 11, 7, 20, 0, tzinfo=UTC)
    assert weekly.relief.left_percent == 80.5
    assert pool.stale is False


def test_chatgpt_pool_reports_every_window_when_no_account_is_ready() -> None:
    accounts = [_account("plus", "plus"), _account("paused", "pro", AccountStatus.PAUSED)]
    latest = {
        "primary": {"plus": _usage("plus", "primary", 40, minutes=300, resets_in=timedelta(hours=2))},
        "secondary": {"plus": _usage("plus", "secondary", 100, minutes=10080, resets_in=timedelta(days=1))},
        "monthly": {},
    }

    pool = chatgpt_pool(accounts=accounts, latest=latest, models=["gpt-6-sol"], pace=None, now=NOW)

    assert pool.accounts.model_dump() == {"total": 1, "ready": 0}
    assert [(window.id, window.left_percent) for window in pool.windows] == [("five_hour", 0.0), ("weekly", 0.0)]


def _claude(source_id: str, *, five_hour: float, seven_day: float, fable: float | None = None) -> ClaudeAccount:
    state = ClaudeState(
        subscription=SubscriptionMetadata(
            rate_limit_tier="default_claude_max_5x", source="bootstrap", observed_at=NOW.replace(tzinfo=UTC)
        ),
        usage=UsageSnapshot(
            five_hour=QuotaWindow(utilization=five_hour, resets_at=NOW.replace(tzinfo=UTC) + timedelta(hours=2)),
            seven_day=QuotaWindow(utilization=seven_day, resets_at=NOW.replace(tzinfo=UTC) + timedelta(hours=11)),
            seven_day_overage_included=(
                QuotaWindow(utilization=fable, resets_at=NOW.replace(tzinfo=UTC) + timedelta(days=2))
                if fable is not None
                else None
            ),
        ),
        usage_updated_at=NOW.replace(tzinfo=UTC) - timedelta(minutes=1),
    )
    return ClaudeAccount(
        source_id=source_id,
        state_json=state.model_dump_json(),
        source=ModelSource(id=source_id, name=source_id, is_enabled=True),
    )


MODELS = ["anthropic/claude-fable-5-1", "anthropic/claude-opus-5-5", "anthropic/claude-sonnet-5-5"]


def test_claude_models_share_one_pool_while_no_model_window_binds() -> None:
    pace = _pace(
        runway_status="runs_dry",
        depletion_eta_hours=7.0,
        next_relief_in_hours=11.0,
        headroom_credits=0.7,
        next_relief_credits=4.3,
        total_full_credits=5.0,
    )

    (pool,) = claude_pools(
        accounts=[_claude("max", five_hour=70, seven_day=86, fable=40)], models=MODELS, pace=pace, now=NOW
    )

    assert (pool.id, pool.label, pool.models) == ("claude", "Claude", MODELS)
    assert [(window.id, window.left_percent) for window in pool.windows] == [("five_hour", 30.0), ("weekly", 14.0)]
    weekly = pool.windows[1]
    assert weekly.exhausts_at == datetime(2026, 11, 7, 18, 0, tzinfo=UTC)
    assert weekly.relief is not None and weekly.relief.left_percent == 100.0


def test_claude_model_window_that_binds_harder_gets_its_own_pool() -> None:
    shared, fable = claude_pools(
        accounts=[_claude("max", five_hour=10, seven_day=20, fable=90)], models=MODELS, pace=None, now=NOW
    )

    assert (shared.id, shared.models) == ("claude", MODELS[1:])
    assert (fable.id, fable.label, fable.models) == ("claude:seven_day_overage_included", "Claude · Fable", MODELS[:1])
    assert [(window.id, window.left_percent) for window in fable.windows] == [("five_hour", 90.0), ("weekly", 10.0)]


def _antigravity(source_id: str, buckets: list[QuotaBucket]) -> AntigravityAccount:
    state = AntigravityState(
        subscription=AntigravitySubscription(
            paid_tier=Tier(id="g1-pro-tier", name="Google AI Pro"), observed_at=NOW.replace(tzinfo=UTC)
        ),
        quota=buckets,
        metadata={"quota": MetadataState(updated_at=NOW.replace(tzinfo=UTC) - timedelta(minutes=2))},
    )
    return AntigravityAccount(
        source_id=source_id,
        state_json=state.model_dump_json(),
        source=ModelSource(id=source_id, name=source_id, is_enabled=True),
    )


def _source_model(slug: str, family: str) -> UpstreamModel:
    return UpstreamModel(
        slug=slug,
        display_name=slug,
        description=slug,
        context_window=1,
        input_modalities=("text",),
        supported_reasoning_levels=(),
        default_reasoning_level=None,
        supports_reasoning_summaries=False,
        support_verbosity=False,
        default_verbosity=None,
        prefer_websockets=True,
        supports_parallel_tool_calls=True,
        supported_in_api=True,
        minimal_client_version=None,
        priority=0,
        available_in_plans=frozenset(),
        source_kind="antigravity",
        source_id="ag",
        raw={"quota_family": family},
    )


def test_antigravity_families_are_separate_pools() -> None:
    weekly_reset = NOW.replace(tzinfo=UTC) + timedelta(days=3)
    account = _antigravity(
        "ag",
        [
            QuotaBucket(family="claude", window="weekly", remaining_fraction=0.25, resets_at=weekly_reset),
            QuotaBucket(family="claude", window="five_hour", remaining_fraction=1.0, resets_at=weekly_reset),
        ],
    )

    gemini, claude = antigravity_pools(
        accounts=[account],
        models=[
            _source_model("antigravity/gemini-3.8-flash", "gemini"),
            _source_model("antigravity/claude-opus-5-5", "claude"),
        ],
        paces=[],
        now=NOW,
    )

    # Google reports no Gemini limit for this account: it serves, without a window to show.
    assert (gemini.label, gemini.accounts.ready, gemini.windows) == ("Antigravity · Gemini", 1, [])
    assert claude.label == "Antigravity · Claude & GPT"
    assert [(window.id, window.left_percent) for window in claude.windows] == [("five_hour", 100.0), ("weekly", 25.0)]
    assert claude.windows[0].resets_at is None


def test_openrouter_pool_reports_prepaid_credits() -> None:
    state = OpenRouterState(
        credits=CreditInfo(total_credits=10.0, total_usage=4.26),
        credits_updated_at=NOW - timedelta(minutes=1),
    )
    account = OpenRouterAccount(
        source_id="or",
        state_json=state.model_dump_json(),
        source=ModelSource(id="or", name="or", is_enabled=True),
    )

    pool = openrouter_pool(accounts=[account], models=["openrouter/z-ai/glm-5.3-flash"])

    assert pool.credits is not None and pool.credits.model_dump() == {"total_usd": 10.0, "used_usd": 4.26}
    assert pool.windows == []
    assert pool.updated_at == (NOW - timedelta(minutes=1)).replace(tzinfo=UTC)
