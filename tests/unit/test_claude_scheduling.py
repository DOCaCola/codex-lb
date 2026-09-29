from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from app.core.balancer import select_account
from app.db.models import ClaudeAccount, DashboardSettings
from app.modules.claude import scheduling
from app.modules.claude.schemas import AccountState, QuotaWindow, UsageSnapshot

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 29, 12, tzinfo=UTC)
MODEL = "anthropic/claude-opus-5"


def account(identifier, *, used=20, hours=24, stale=False, family=None):
    state = AccountState(
        usage=UsageSnapshot(
            five_hour=QuotaWindow(utilization=10, resets_at=NOW + timedelta(hours=2)),
            seven_day=QuotaWindow(utilization=used, resets_at=NOW + timedelta(hours=hours)),
            seven_day_opus=QuotaWindow(utilization=family, resets_at=NOW + timedelta(hours=3))
            if family is not None
            else None,
        ),
        usage_updated_at=NOW - timedelta(minutes=10 if stale else 1),
    )
    return ClaudeAccount(source_id=identifier, state_json=state.model_dump_json(), routing_policy="normal")


@pytest.mark.parametrize("strategy", ["round_robin", "capacity_weighted", "usage_weighted", "relative_availability"])
def test_account_policy_is_applied_by_shared_scheduler(strategy):
    normal, burn, preserve = account("normal"), account("burn"), account("preserve")
    burn.routing_policy = "burn_first"
    preserve.routing_policy = "preserve"
    assert choose([normal, burn, preserve], strategy) is burn
    assert choose([normal, preserve], strategy) is normal
    assert choose([preserve], strategy) is preserve


def settings(strategy):
    return DashboardSettings(
        routing_strategy=strategy,
        prefer_earlier_reset_accounts=False,
        prefer_earlier_reset_window="secondary",
        relative_availability_power=1.0,
        relative_availability_top_k=1,
    )


def choose(accounts, strategy):
    return scheduling.choose(
        accounts, settings(strategy), now=NOW, client_scope="key", conversation_id="c", model=MODEL
    )


@pytest.mark.parametrize(
    "strategy",
    [
        "capacity_weighted",
        "relative_availability",
        "usage_weighted",
        "round_robin",
        "fill_first",
        "sequential_drain",
        "reset_drain",
        "single_account",
    ],
)
def test_shared_strategy_receives_normalized_claude_data(monkeypatch, strategy):
    spy = Mock(wraps=select_account)
    monkeypatch.setattr(scheduling, "select_account", spy)
    accounts = [account("a", family=70), account("b", used=40)]
    assert choose(accounts, strategy) in accounts
    candidates = spy.call_args.args[0]
    assert all(candidate.capacity_credits == 1.0 and candidate.plan_type is None for candidate in candidates)
    assert candidates[0].secondary_used_percent == 70
    assert candidates[0].secondary_reset_at == int((NOW + timedelta(hours=3)).timestamp())
    assert candidates[0].used_percent == 10 and candidates[0].primary_window_minutes == 300
    assert spy.call_args.kwargs["routing_strategy"] == strategy
    assert spy.call_args.kwargs["selection_seed"] is None


@pytest.mark.parametrize(
    "strategy", ["capacity_weighted", "relative_availability", "usage_weighted", "fill_first", "reset_drain"]
)
def test_known_quota_ranks_before_stale_and_unknown(strategy):
    known = account("known", used=90)
    assert choose([account("stale", used=0, stale=True), known], strategy) is known


def test_stale_only_data_is_explicitly_neutral(monkeypatch):
    spy = Mock(wraps=select_account)
    monkeypatch.setattr(scheduling, "select_account", spy)
    choose([account("a", stale=True), account("b", stale=True)], "capacity_weighted")
    assert all(
        candidate.used_percent is None
        and candidate.secondary_used_percent is None
        and candidate.secondary_reset_at is None
        for candidate in spy.call_args.args[0]
    )
    assert spy.call_args.kwargs["selection_seed"] is not None


def test_relative_availability_prefers_more_remaining_capacity_per_time():
    earlier = account("earlier", used=20, hours=2)
    later = account("later", used=80, hours=20)
    assert choose([later, earlier], "relative_availability") is earlier


def test_round_robin_keeps_stale_accounts_and_uses_recency():
    older = account("older", stale=True)
    newer = account("newer")
    older.last_selected_at = NOW - timedelta(minutes=5)
    newer.last_selected_at = NOW - timedelta(minutes=1)
    assert choose([newer, older], "round_robin") is older


def test_reset_drain_uses_reset_day_before_usage():
    earlier = account("earlier", used=20, hours=2)
    later = account("later", used=80, hours=48)
    assert choose([later, earlier], "reset_drain") is earlier
