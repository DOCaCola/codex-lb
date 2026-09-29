"""Adapt eligible Claude accounts to the shared routing strategy."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

from app.core.balancer import AccountState as Candidate
from app.core.balancer import ResetPreferenceWindow, RoutingStrategy, select_account
from app.db.models import AccountStatus, ClaudeAccount, DashboardSettings
from app.modules.claude.quota import applicable_windows, quota_status
from app.modules.claude.schemas import AccountState


def choose(
    accounts: list[ClaudeAccount],
    settings: DashboardSettings,
    *,
    now: datetime,
    client_scope: str,
    conversation_id: str,
    model: str,
) -> ClaudeAccount:
    candidates: list[Candidate] = []
    complete: set[str] = set()
    for account in accounts:
        windows = quota_status(AccountState.model_validate_json(account.state_json), now=now).windows
        fresh = {window.name: window for window in windows if window.freshness == "fresh"}
        primary = fresh.get("five_hour")
        weekly = [window for name, window in fresh.items() if name != "five_hour" and name in applicable_windows(model)]
        secondary = max(weekly, key=lambda window: window.utilization or 0, default=None)
        if primary is not None and "seven_day" in fresh:
            complete.add(account.source_id)
        candidates.append(
            Candidate(
                account_id=account.source_id,
                status=AccountStatus.ACTIVE,
                used_percent=primary.utilization if primary else None,
                primary_reset_at=int(primary.resets_at.timestamp()) if primary and primary.resets_at else None,
                primary_window_minutes=300,
                secondary_used_percent=secondary.utilization if secondary else None,
                secondary_reset_at=int(secondary.resets_at.timestamp()) if secondary and secondary.resets_at else None,
                capacity_credits=1.0,
                last_selected_at=account.last_selected_at.replace(tzinfo=UTC).timestamp()
                if account.last_selected_at
                else None,
            )
        )
    strategy = cast(RoutingStrategy, settings.routing_strategy)
    quota_ranked = strategy not in ("round_robin", "single_account", "sequential_drain")
    neutral = quota_ranked and not complete
    if quota_ranked and complete:
        candidates = [candidate for candidate in candidates if candidate.account_id in complete]
    elif neutral:
        for candidate in candidates:
            candidate.used_percent = candidate.secondary_used_percent = None
            candidate.primary_reset_at = candidate.secondary_reset_at = None
    result = select_account(
        candidates,
        now=now.timestamp(),
        routing_strategy=strategy,
        prefer_earlier_reset=settings.prefer_earlier_reset_accounts,
        prefer_earlier_reset_window=cast(ResetPreferenceWindow, settings.prefer_earlier_reset_window),
        relative_availability_power=settings.relative_availability_power,
        relative_availability_top_k=settings.relative_availability_top_k,
        allow_backoff_fallback=False,
        selection_seed=json.dumps([client_scope, conversation_id, model]) if neutral else None,
    )
    assert result.account is not None  # Provider eligibility already admitted this nonempty pool.
    return next(account for account in accounts if account.source_id == result.account.account_id)
