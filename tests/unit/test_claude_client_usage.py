from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import ClaudeAccount, ModelSource
from app.modules.claude.client_usage import BASE_WINDOWS, claude_pool_rate_limit_headers
from app.modules.claude.quota import applicable_windows
from app.modules.claude.schemas import AccountState, QuotaWindow, SubscriptionMetadata, UsageSnapshot

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 6, 12, 0, 0, tzinfo=UTC)
FIVE_HOUR_RESET = NOW + timedelta(hours=2)
WEEKLY_RESET = NOW + timedelta(days=3)
OPUS_RESET = NOW + timedelta(days=2)


def _account(
    source_id: str,
    tier: str,
    *,
    five_hour: float,
    seven_day: float,
    seven_day_opus: float | None = None,
    enabled: bool = True,
) -> ClaudeAccount:
    state = AccountState(
        subscription=SubscriptionMetadata(rate_limit_tier=tier, source="bootstrap", observed_at=NOW),
        usage=UsageSnapshot(
            five_hour=QuotaWindow(utilization=five_hour, resets_at=FIVE_HOUR_RESET),
            seven_day=QuotaWindow(utilization=seven_day, resets_at=WEEKLY_RESET),
            seven_day_opus=(
                QuotaWindow(utilization=seven_day_opus, resets_at=OPUS_RESET) if seven_day_opus is not None else None
            ),
        ),
        usage_updated_at=NOW - timedelta(minutes=1),
    )
    return ClaudeAccount(
        source_id=source_id,
        state_json=state.model_dump_json(),
        source=ModelSource(id=source_id, name=source_id, is_enabled=enabled),
    )


def test_pool_is_weighted_in_pro_units() -> None:
    headers = claude_pool_rate_limit_headers(
        [
            _account("pro", "default_claude_pro", five_hour=50, seven_day=40),
            _account("max5", "default_claude_max_5x", five_hour=10, seven_day=20),
            _account("paused", "default_claude_max_20x", five_hour=90, seven_day=90, enabled=False),
        ],
        windows=BASE_WINDOWS,
        now=NOW,
    )

    assert float(headers["x-codex-primary-used-percent"]) == pytest.approx((0.5 + 0.5) / 6 * 100)
    assert headers["x-codex-primary-window-minutes"] == "300"
    assert headers["x-codex-primary-reset-at"] == str(int(FIVE_HOUR_RESET.timestamp()))
    assert float(headers["x-codex-secondary-used-percent"]) == pytest.approx((0.4 + 1.0) / 6 * 100)
    assert headers["x-codex-secondary-window-minutes"] == "10080"


def test_model_specific_weekly_limit_binds() -> None:
    account = _account("max5", "default_claude_max_5x", five_hour=10, seven_day=40, seven_day_opus=90)

    opus = claude_pool_rate_limit_headers([account], windows=applicable_windows("claude-opus-5-5"), now=NOW)
    haiku = claude_pool_rate_limit_headers([account], windows=applicable_windows("claude-haiku-5-5"), now=NOW)

    assert float(opus["x-codex-secondary-used-percent"]) == pytest.approx(90.0)
    assert opus["x-codex-secondary-reset-at"] == str(int(OPUS_RESET.timestamp()))
    assert float(haiku["x-codex-secondary-used-percent"]) == pytest.approx(40.0)


def test_exhausted_account_counts_as_fully_used() -> None:
    headers = claude_pool_rate_limit_headers(
        [
            _account("spent", "default_claude_pro", five_hour=0, seven_day=100),
            _account("fresh", "default_claude_pro", five_hour=0, seven_day=0),
        ],
        windows=BASE_WINDOWS,
        now=NOW,
    )

    assert float(headers["x-codex-primary-used-percent"]) == pytest.approx(50.0)
    assert "x-codex-primary-reset-at" not in headers


def test_no_pooled_accounts_reports_nothing() -> None:
    assert claude_pool_rate_limit_headers([], windows=BASE_WINDOWS, now=NOW) == {}
