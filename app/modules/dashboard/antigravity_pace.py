"""Antigravity weekly quota pace, one pool per model family in Pro units.

Google limits Gemini, Gemini 4 Argon and Claude & GPT separately: each family
has its own weekly window and spending one does not block the others, so their
windows are never summed. A family's pool holds the accounts that report its
weekly window, weighted by plan (Pro 1, Ultra 5x 5, Ultra 20x 20); plans
without a published multiple are not pooled. Eligibility mirrors the Claude
pace: disabled accounts are inactive and readings from a failed or missed poll
are stale.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import get_args

from app.core.utils.time import naive_utc_to_epoch
from app.db.models import AntigravityAccount, AntigravityQuotaHistory
from app.modules.antigravity.quota import current_buckets, plan_type, quota_fresh, quota_weight
from app.modules.antigravity.schemas import AccountState, QuotaFamily
from app.modules.dashboard.schemas import AntigravityFamilyPace
from app.modules.dashboard.weekly_pace import PaceAccountInput, build_weekly_pace, positive_used_percent_delta

QUOTA_FAMILIES: tuple[QuotaFamily, ...] = get_args(QuotaFamily)
WEEKLY_WINDOW_MINUTES = 10_080
# One Pro account's weekly window in Pro units.
PRO_ACCOUNT_UNITS = 1.0


@dataclass(frozen=True)
class _QuotaSample:
    recorded_at: datetime
    used_percent: float
    reset_at: int | None
    window_minutes: int | None


def build_antigravity_weekly_pace(
    *,
    accounts: Sequence[AntigravityAccount],
    weekly_history: Mapping[tuple[str, QuotaFamily], Sequence[AntigravityQuotaHistory]],
    now: datetime,
    working_days: set[int] | None,
    smoothing_window_minutes: int,
) -> list[AntigravityFamilyPace]:
    """One pace per family with at least one eligible weekly window, in family order.

    ``weekly_history`` holds each account's weekly observations of one family,
    ordered by observation time; ``now`` is naive UTC like the history timestamps.
    """

    status_now = now.replace(tzinfo=UTC)
    states = {account.source_id: AccountState.model_validate_json(account.state_json) for account in accounts}
    paces: list[AntigravityFamilyPace] = []
    for family in QUOTA_FAMILIES:
        inputs: list[PaceAccountInput] = []
        trailing_demand: dict[str, float] = {}
        stale_account_count = 0
        inactive_account_count = 0
        for account in accounts:
            state = states[account.source_id]
            weight = quota_weight(plan_type(state.subscription))
            if weight is None:
                continue
            weekly = next(
                (
                    bucket
                    for bucket in current_buckets(state, status_now)
                    if bucket.family == family and bucket.window == "weekly"
                ),
                None,
            )
            if weekly is None or weekly.resets_at is None:
                continue
            if not account.source.is_enabled:
                inactive_account_count += 1
                continue
            if not quota_fresh(state, status_now):
                stale_account_count += 1
                continue

            samples = [_sample(row) for row in weekly_history.get((account.source_id, family), ())]
            inputs.append(
                PaceAccountInput(
                    account_id=account.source_id,
                    full_units=float(weight),
                    remaining_units=weight * weekly.remaining_fraction,
                    reset_at_ms=weekly.resets_at.timestamp() * 1000.0,
                    window_ms=WEEKLY_WINDOW_MINUTES * 60_000.0,
                    history=samples,
                )
            )
            trailing_demand[account.source_id] = positive_used_percent_delta(samples)

        pace = build_weekly_pace(
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
        if pace is not None:
            paces.append(AntigravityFamilyPace(family=family, pace=pace))
    return paces


def _sample(row: AntigravityQuotaHistory) -> _QuotaSample:
    # Reported deadlines jitter between polls; the minute identifies the window instance.
    reset_at = round(naive_utc_to_epoch(row.resets_at) / 60) * 60 if row.resets_at is not None else None
    return _QuotaSample(
        recorded_at=row.observed_at,
        used_percent=row.used_percent,
        reset_at=reset_at,
        window_minutes=WEEKLY_WINDOW_MINUTES,
    )
