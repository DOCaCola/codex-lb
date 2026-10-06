"""Claude weekly quota pace, pooled in Pro units.

Each account's seven-day subscription window counts as its plan weight in Pro
units (Pro 1, Max 5x 5, Max 20x 20). Plans without a stated multiplier are not
pooled. Eligibility mirrors the Codex pace: disabled accounts are inactive and
windows without a fresh observation are stale.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.utils.time import naive_utc_to_epoch
from app.db.models import ClaudeAccount, ClaudeQuotaHistory
from app.modules.claude.quota import quota_status
from app.modules.claude.schemas import AccountState
from app.modules.claude.subscription import quota_weight, subscription_plan
from app.modules.dashboard.schemas import WeeklyCreditPaceResponse
from app.modules.dashboard.weekly_pace import PaceAccountInput, build_weekly_pace

SEVEN_DAY_WINDOW_MINUTES = 10_080
# One Pro account's weekly window in Pro units.
PRO_ACCOUNT_UNITS = 1.0


@dataclass(frozen=True)
class _QuotaSample:
    recorded_at: datetime
    used_percent: float
    reset_at: int | None
    window_minutes: int | None


def build_claude_weekly_pace(
    *,
    accounts: Sequence[ClaudeAccount],
    seven_day_history: Mapping[str, Sequence[ClaudeQuotaHistory]],
    now: datetime,
    working_days: set[int] | None,
    smoothing_window_minutes: int,
) -> WeeklyCreditPaceResponse | None:
    """Pace over enabled, plan-weighted accounts with a fresh seven-day window.

    ``seven_day_history`` holds one provenance stream per account, ordered by
    observation time, covering exactly the trailing-demand window; ``now`` is
    naive UTC like the history timestamps.
    """

    inputs: list[PaceAccountInput] = []
    trailing_demand: dict[str, float] = {}
    stale_account_count = 0
    inactive_account_count = 0
    status_now = now.replace(tzinfo=UTC)

    for account in accounts:
        state = AccountState.model_validate_json(account.state_json)
        weight = quota_weight(subscription_plan(state.subscription))
        if weight is None:
            continue
        window = next(window for window in quota_status(state, now=status_now).windows if window.name == "seven_day")
        if window.freshness == "unknown" or window.utilization is None or window.resets_at is None:
            continue
        if not account.source.is_enabled:
            inactive_account_count += 1
            continue
        if window.freshness == "stale":
            stale_account_count += 1
            continue

        samples = [_sample(row) for row in seven_day_history.get(account.source_id, ())]
        inputs.append(
            PaceAccountInput(
                account_id=account.source_id,
                full_units=float(weight),
                remaining_units=weight * (1.0 - window.utilization / 100.0),
                reset_at_ms=window.resets_at.timestamp() * 1000.0,
                window_ms=SEVEN_DAY_WINDOW_MINUTES * 60_000.0,
                history=samples,
            )
        )
        trailing_demand[account.source_id] = _positive_used_percent_delta(samples)

    return build_weekly_pace(
        accounts=inputs,
        now=now,
        unit="pro_units",
        pro_account_units=PRO_ACCOUNT_UNITS,
        stale_account_count=stale_account_count,
        inactive_account_count=inactive_account_count,
        trailing_demand_used_percent_by_account=trailing_demand,
        working_days=working_days,
        smoothing_window_minutes=smoothing_window_minutes,
    )


def _sample(row: ClaudeQuotaHistory) -> _QuotaSample:
    # Reported deadlines jitter by under a second between polls; the minute
    # identifies the window instance so smoothing and burn do not restart.
    reset_at = round(naive_utc_to_epoch(row.resets_at) / 60) * 60 if row.resets_at is not None else None
    return _QuotaSample(
        recorded_at=row.observed_at,
        used_percent=row.used_percent,
        reset_at=reset_at,
        window_minutes=SEVEN_DAY_WINDOW_MINUTES,
    )


def _positive_used_percent_delta(samples: Sequence[_QuotaSample]) -> float:
    return sum(
        max(0.0, current.used_percent - previous.used_percent) for previous, current in zip(samples, samples[1:])
    )
