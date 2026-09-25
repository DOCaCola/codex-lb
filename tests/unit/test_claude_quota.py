from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.modules.claude.quota import model_quota, quota_status
from app.modules.claude.schemas import AccountState, ModelSelection, QuotaWindow, UsageSnapshot

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 25, 12, tzinfo=UTC)


def state(**windows):
    return AccountState(
        usage=UsageSnapshot(**windows),
        usage_updated_at=NOW,
        selections=[ModelSelection(model=model) for model in ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5")],
    )


def test_model_specific_quota_does_not_disable_other_families():
    status = quota_status(
        state(seven_day_opus=QuotaWindow(utilization=100, resets_at=NOW + timedelta(hours=2))), now=NOW
    )
    assert [model.blocked for model in status.models] == [True, False, False]
    assert status.models[0].blocking_windows == ["seven_day_opus"]
    assert model_quota("anthropic/claude-opus-5", status.windows).blocked


def test_shared_windows_gate_all_models_until_latest_reset():
    status = quota_status(
        state(
            five_hour=QuotaWindow(utilization=100, resets_at=NOW + timedelta(hours=1)),
            seven_day=QuotaWindow(utilization=120, resets_at=NOW + timedelta(hours=2)),
        ),
        now=NOW,
    )
    assert all(model.blocked and model.retry_at == NOW + timedelta(hours=2) for model in status.models)


def test_missing_usage_and_null_windows_are_unknown_not_denied_entitlement():
    status = quota_status(state(), now=NOW)
    assert all(window.utilization is None and window.freshness == "unknown" for window in status.windows)
    assert not any(model.blocked for model in status.models)


def test_stale_exhaustion_remains_blocked_until_reset_without_invented_zero():
    observed = state(seven_day=QuotaWindow(utilization=100, resets_at=NOW + timedelta(hours=2)))
    status = quota_status(observed, now=NOW + timedelta(minutes=6))
    assert status.windows[1].freshness == "stale"
    assert all(model.blocked for model in status.models)
    status = quota_status(observed, now=NOW + timedelta(hours=2))
    assert status.windows[1].freshness == "unknown"
    assert status.windows[1].utilization == 100
    assert not any(model.blocked for model in status.models)


def test_unknown_reset_does_not_report_a_false_retry_time():
    status = quota_status(
        state(
            five_hour=QuotaWindow(utilization=100),
            seven_day=QuotaWindow(utilization=100, resets_at=NOW + timedelta(hours=2)),
        ),
        now=NOW,
    )
    assert all(model.blocked and model.retry_at is None for model in status.models)


def test_monitor_error_marks_last_snapshot_stale():
    observed = state(five_hour=QuotaWindow(utilization=20))
    observed.usage_error = "Metadata unavailable"
    status = quota_status(observed, now=NOW)
    assert status.windows[0].freshness == "stale"
    assert not any(model.blocked for model in status.models)


def test_unknown_provider_windows_are_preserved_without_guessing_scope():
    observed = state(seven_day_new_family={"utilization": 100, "resets_at": "2026-09-26T12:00:00Z"})
    assert "seven_day_new_family" in observed.usage.model_dump()
    assert not any(model.blocked for model in quota_status(observed, now=NOW).models)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_invalid_utilization_rejected(value):
    with pytest.raises(ValidationError):
        QuotaWindow(utilization=value)


def test_ambiguous_reset_timezone_rejected():
    with pytest.raises(ValidationError):
        QuotaWindow(utilization=1, resets_at="2026-09-25T12:00:00")
