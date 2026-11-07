"""The quota snapshot codex-lb shows desktop integrations for a proxy API key.

Only stored quota readings and request logs are read; no provider is asked, so
clients may poll it. Each pool is limited independently and lists the models it
serves, so a client can tell which pool serves a thread from the thread's model.
The weekly outlook (when a pool runs dry, how much the next reset returns) is the
dashboard's weekly pace over the same accounts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast, get_args

from app.core import usage as usage_core
from app.core.openai.model_registry import UpstreamModel
from app.core.usage.refresh_policy import usage_freshness_horizon_seconds
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus, AntigravityAccount, ClaudeAccount, OpenRouterAccount, UsageHistory
from app.db.session import detach_session_objects, get_background_session
from app.modules.antigravity.quota import family_quota, plan_type, quota_fresh, quota_weight
from app.modules.antigravity.schemas import AccountState as AntigravityState
from app.modules.antigravity.schemas import QuotaBucket, QuotaFamily
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.client_usage import BASE_WINDOWS, ClaudePool, ClaudePoolWindow, summarize_claude_pool
from app.modules.claude.quota import applicable_windows
from app.modules.claude.schemas import WindowName
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import AntigravityFamilyPace, WeeklyCreditPaceResponse
from app.modules.dashboard.service import DashboardService
from app.modules.openrouter.repository import OpenRouterRepository
from app.modules.openrouter.schemas import AccountState as OpenRouterState
from app.modules.proxy.helpers import _select_accounts_for_limits
from app.modules.proxy.schemas import (
    CodexLbUsageAccounts,
    CodexLbUsageCredits,
    CodexLbUsagePool,
    CodexLbUsageRelief,
    CodexLbUsageResponse,
    CodexLbUsageToday,
    CodexLbUsageWindow,
    CodexLbUsageWindowId,
)
from app.modules.usage.mappers import usage_history_to_window_row

FIVE_HOUR_SECONDS = 5 * 3600
WEEK_SECONDS = 7 * 86400
# Model source kinds whose quota codex-lb tracks.
USAGE_SOURCE_KINDS = frozenset({"claude", "antigravity", "openrouter"})
# Stored usage windows after weekly-only accounts are normalized, and their client names.
_CHATGPT_WINDOWS: tuple[tuple[str, CodexLbUsageWindowId], ...] = (
    ("primary", "five_hour"),
    ("secondary", "weekly"),
    ("monthly", "monthly"),
)
_ANTIGRAVITY_FAMILIES: tuple[QuotaFamily, ...] = get_args(QuotaFamily)
_ANTIGRAVITY_FAMILY_LABELS: dict[QuotaFamily, str] = {
    "gemini": "Gemini",
    "argon": "Gemini Argon",
    "claude": "Claude & GPT",
}
# Model-specific Claude weekly windows, named after the models they limit.
_CLAUDE_WINDOW_LABELS: dict[WindowName, str] = {
    "seven_day_opus": "Opus",
    "seven_day_sonnet": "Sonnet",
    "seven_day_overage_included": "Fable",
}


@dataclass(frozen=True, slots=True)
class UsageScope:
    """What the requesting key can use: Codex accounts (None: all) and the models of each pool."""

    account_ids: frozenset[str] | None
    native_models: Sequence[str]
    source_models: Sequence[UpstreamModel]

    @property
    def source_ids(self) -> frozenset[str]:
        return frozenset(model.source_id for model in self.source_models if model.source_id is not None)

    def models_of(self, kind: str) -> list[str]:
        return sorted(model.slug for model in self.source_models if model.source_kind == kind)


async def build_usage_snapshot(
    scope: UsageScope,
    *,
    api_key: ApiKeyData | None,
    since: datetime,
) -> CodexLbUsageResponse:
    now = utcnow()
    async with get_background_session() as session:
        repo = DashboardRepository(session)
        accounts = [
            account
            for account in await repo.list_accounts()
            if scope.account_ids is None or account.id in scope.account_ids
        ]
        latest = {window: await repo.latest_usage_by_account(window) for window in ("primary", "secondary", "monthly")}
        source_ids = scope.source_ids
        claude_accounts = [account for account in await repo.list_claude_accounts() if account.source_id in source_ids]
        antigravity_accounts = [
            account for account in await repo.list_antigravity_accounts() if account.source_id in source_ids
        ]
        openrouter_accounts = [
            account
            for account in await OpenRouterRepository(session).list_accounts()
            if account.source_id in source_ids
        ]
        paces = await DashboardService(repo).get_weekly_paces(account_ids=scope.account_ids, source_ids=source_ids)
        today = (
            await ApiKeysRepository(session).usage_7d(api_key.id, since.astimezone(UTC).replace(tzinfo=None), now)
            if api_key is not None
            else None
        )
        # Closing the session rolls back its read transaction, which would expire the loaded rows.
        detach_session_objects(session)

    pools: list[CodexLbUsagePool] = []
    if scope.native_models:
        pools.append(
            chatgpt_pool(accounts=accounts, latest=latest, models=scope.native_models, pace=paces.codex, now=now)
        )
    pools.extend(claude_pools(accounts=claude_accounts, models=scope.models_of("claude"), pace=paces.claude, now=now))
    pools.extend(
        antigravity_pools(
            accounts=antigravity_accounts,
            models=[model for model in scope.source_models if model.source_kind == "antigravity"],
            paces=paces.antigravity,
            now=now,
        )
    )
    if openrouter_models := scope.models_of("openrouter"):
        pools.append(openrouter_pool(accounts=openrouter_accounts, models=openrouter_models))
    return CodexLbUsageResponse(
        generated_at=_aware(now),
        pools=pools,
        today=(
            CodexLbUsageToday(since=since, requests=today.total_requests, cost_usd=today.total_cost_usd)
            if today is not None
            else None
        ),
    )


def chatgpt_pool(
    *,
    accounts: Sequence[Account],
    latest: Mapping[str, Mapping[str, UsageHistory]],
    models: Sequence[str],
    pace: WeeklyCreditPaceResponse | None,
    now: datetime,
) -> CodexLbUsagePool:
    """The ChatGPT accounts as Codex clients see their pooled limits.

    A window that only blocked accounts report does not limit what the pool can
    serve now, so it is left out while another account is ready.
    """
    account_map = {account.id: account for account in _select_accounts_for_limits(accounts)}
    raw = {
        window: [
            usage_history_to_window_row(entry)
            for account_id, entry in latest[window].items()
            if account_id in account_map
        ]
        for window in ("primary", "secondary", "monthly")
    }
    primary, secondary = usage_core.normalize_weekly_only_rows(raw["primary"], raw["secondary"])
    now_epoch = int(_aware(now).timestamp())
    summary = usage_core.summarize_client_pool(
        primary_rows=primary,
        secondary_rows=secondary,
        monthly_rows=raw["monthly"],
        account_map=account_map,
        now_epoch=now_epoch,
    )
    current = {
        window: usage_core.expire_elapsed_window_rows(rows, now_epoch=now_epoch)
        for window, rows in (("primary", primary), ("secondary", secondary), ("monthly", raw["monthly"]))
    }
    exhausted = {
        row.account_id
        for window, rows in current.items()
        for row in rows
        if (row.used_percent or 0.0) >= 100.0
        and usage_core.capacity_for_plan(account_map[row.account_id].plan_type, window) is not None
    }
    ready = {
        account_id
        for account_id, account in account_map.items()
        if account.status == AccountStatus.ACTIVE and account_id not in exhausted
    }
    windows: list[CodexLbUsageWindow] = []
    for (window, window_id), pooled in zip(_CHATGPT_WINDOWS, (summary.primary, summary.secondary, summary.monthly)):
        if pooled is None or pooled.used_percent is None:
            continue
        if ready and not any(row.account_id in ready for row in current[window]):
            continue
        # Pooled windows resolve their length, falling back to the window's default.
        window_minutes = pooled.window_minutes
        assert window_minutes is not None
        windows.append(
            _window(
                window_id,
                window_seconds=window_minutes * 60,
                used_percent=pooled.used_percent,
                reset_at=pooled.reset_at,
                pace=pace if window_id == "weekly" else None,
                now=now,
            )
        )
    recorded = [row.recorded_at for rows in current.values() for row in rows if row.recorded_at is not None]
    updated_at = max(recorded, default=None)
    return CodexLbUsagePool(
        id="chatgpt",
        kind="chatgpt",
        label="ChatGPT",
        models=sorted(models),
        accounts=CodexLbUsageAccounts(total=len(account_map), ready=len(ready)),
        windows=windows,
        updated_at=_aware(updated_at) if updated_at is not None else None,
        stale=updated_at is None or now - updated_at > timedelta(seconds=usage_freshness_horizon_seconds()),
    )


def claude_pools(
    *,
    accounts: Sequence[ClaudeAccount],
    models: Sequence[str],
    pace: WeeklyCreditPaceResponse | None,
    now: datetime,
) -> list[CodexLbUsagePool]:
    """The Claude accounts, split where a model-specific weekly limit binds harder than the shared one.

    Opus, Sonnet and Fable can each have their own weekly window. A model whose
    limits read the same as the shared windows stays in the shared pool.
    """
    status_now = _aware(now)
    shared = summarize_claude_pool(accounts, windows=BASE_WINDOWS, now=status_now)
    groups: dict[WindowName | None, tuple[ClaudePool, list[str]]] = {}
    for model in models:
        windows = applicable_windows(model)
        # Each model adds at most one window of its own to the shared ones.
        extra = next(iter(windows - BASE_WINDOWS), None)
        pool = summarize_claude_pool(accounts, windows=windows, now=status_now) if extra is not None else shared
        key = None if pool.five_hour == shared.five_hour and pool.weekly == shared.weekly else extra
        groups.setdefault(key, (shared if key is None else pool, []))[1].append(model)
    return [
        _claude_pool(
            "claude" if extra is None else "claude:" + extra,
            "Claude" if extra is None else "Claude · " + _CLAUDE_WINDOW_LABELS[extra],
            pool,
            group_models,
            # The pace follows the shared seven-day window.
            pace=pace if extra is None else None,
            now=now,
        )
        for extra, (pool, group_models) in sorted(groups.items(), key=lambda item: item[0] or "")
    ]


def _claude_pool(
    pool_id: str,
    label: str,
    pool: ClaudePool,
    models: Sequence[str],
    *,
    pace: WeeklyCreditPaceResponse | None,
    now: datetime,
) -> CodexLbUsagePool:
    pooled: tuple[tuple[CodexLbUsageWindowId, int, ClaudePoolWindow | None], ...] = (
        ("five_hour", FIVE_HOUR_SECONDS, pool.five_hour),
        ("weekly", WEEK_SECONDS, pool.weekly),
    )
    return CodexLbUsagePool(
        id=pool_id,
        kind="claude",
        label=label,
        models=sorted(models),
        accounts=CodexLbUsageAccounts(total=pool.account_count, ready=pool.ready_account_count),
        windows=[
            _window(
                window_id,
                window_seconds=seconds,
                used_percent=window.used_percent,
                reset_at=window.reset_at,
                pace=pace if window_id == "weekly" else None,
                now=now,
            )
            for window_id, seconds, window in pooled
            if window is not None
        ],
        updated_at=pool.observed_at,
        stale=pool.stale,
    )


def antigravity_pools(
    *,
    accounts: Sequence[AntigravityAccount],
    models: Sequence[UpstreamModel],
    paces: Sequence[AntigravityFamilyPace],
    now: datetime,
) -> list[CodexLbUsagePool]:
    """One pool per model family with models: Google limits each family separately."""
    families: dict[QuotaFamily, list[str]] = {}
    for model in models:
        family = cast(QuotaFamily, model.raw["quota_family"])
        assert family in _ANTIGRAVITY_FAMILIES
        families.setdefault(family, []).append(model.slug)
    status_now = _aware(now)
    states = [
        (account, AntigravityState.model_validate_json(account.state_json))
        for account in accounts
        if account.source.is_enabled
    ]
    pace_by_family = {entry.family: entry.pace for entry in paces}
    pools: list[CodexLbUsagePool] = []
    for family in _ANTIGRAVITY_FAMILIES:
        if family not in families:
            continue
        five_hour = _WeightedWindow()
        weekly = _WeightedWindow()
        total = ready = 0
        updated: list[datetime] = []
        stale = False
        for account, state in states:
            quota = family_quota(state, family, status_now)
            total += 1
            ready += not quota.blocked and account.hold is None
            weight = quota_weight(plan_type(state.subscription))
            # Plans without a published size are not pooled, like in the weekly pace.
            if weight is not None:
                five_hour.add(weight, quota.five_hour, exhausted=quota.blocked)
                weekly.add(weight, quota.weekly, exhausted=quota.blocked)
            metadata = state.metadata.get("quota")
            if metadata is not None and metadata.updated_at is not None:
                updated.append(metadata.updated_at)
            stale = stale or not quota_fresh(state, status_now)
        pooled: tuple[tuple[CodexLbUsageWindowId, int, _WeightedWindow], ...] = (
            ("five_hour", FIVE_HOUR_SECONDS, five_hour),
            ("weekly", WEEK_SECONDS, weekly),
        )
        pools.append(
            CodexLbUsagePool(
                id="antigravity:" + family,
                kind="antigravity",
                label="Antigravity" if len(families) == 1 else "Antigravity · " + _ANTIGRAVITY_FAMILY_LABELS[family],
                models=sorted(families[family]),
                accounts=CodexLbUsageAccounts(total=total, ready=ready),
                windows=[
                    _window(
                        window_id,
                        window_seconds=seconds,
                        used_percent=window.used_percent,
                        reset_at=window.reset_at,
                        pace=pace_by_family.get(family) if window_id == "weekly" else None,
                        now=now,
                    )
                    for window_id, seconds, window in pooled
                    if window.capacity > 0
                ],
                updated_at=_aware(max(updated)) if updated else None,
                stale=stale,
            )
        )
    return pools


def openrouter_pool(*, accounts: Sequence[OpenRouterAccount], models: Sequence[str]) -> CodexLbUsagePool:
    states = [
        OpenRouterState.model_validate_json(account.state_json) for account in accounts if account.source.is_enabled
    ]
    credits = [state.credits for state in states if state.credits is not None]
    updated = [state.credits_updated_at for state in states if state.credits_updated_at is not None]
    return CodexLbUsagePool(
        id="openrouter",
        kind="openrouter",
        label="OpenRouter",
        models=sorted(models),
        accounts=CodexLbUsageAccounts(
            total=len(states),
            ready=sum(
                state.credits is None or state.credits.total_usage < state.credits.total_credits for state in states
            ),
        ),
        windows=[],
        credits=(
            CodexLbUsageCredits(
                total_usd=sum(credit.total_credits for credit in credits),
                used_usd=sum(credit.total_usage for credit in credits),
            )
            if credits
            else None
        ),
        updated_at=_aware(max(updated)) if updated else None,
        stale=any(state.credits_error is not None for state in states),
    )


@dataclass
class _WeightedWindow:
    capacity: float = 0.0
    used: float = 0.0
    reset_at: int | None = None

    def add(self, weight: int, bucket: QuotaBucket | None, *, exhausted: bool) -> None:
        if bucket is None:
            return
        self.capacity += weight
        self.used += weight * (100.0 if exhausted else bucket.used_percent) / 100.0
        if bucket.used_percent > 0 and bucket.resets_at is not None:
            reset_at = int(bucket.resets_at.timestamp())
            self.reset_at = reset_at if self.reset_at is None else min(self.reset_at, reset_at)

    @property
    def used_percent(self) -> float:
        return self.used / self.capacity * 100.0


def _window(
    window_id: CodexLbUsageWindowId,
    *,
    window_seconds: int,
    used_percent: float,
    reset_at: int | None,
    pace: WeeklyCreditPaceResponse | None,
    now: datetime,
) -> CodexLbUsageWindow:
    exhausts_at = None
    relief = None
    if pace is not None:
        if pace.runway_status == "runs_dry" and pace.depletion_eta_hours is not None:
            exhausts_at = _hours_after(now, pace.depletion_eta_hours)
        if pace.next_relief_in_hours is not None:
            relief = CodexLbUsageRelief(
                at=_hours_after(now, pace.next_relief_in_hours),
                left_percent=_percent(
                    100.0 * (pace.headroom_credits + pace.next_relief_credits) / pace.total_full_credits
                ),
            )
    return CodexLbUsageWindow(
        id=window_id,
        window_seconds=window_seconds,
        left_percent=_percent(100.0 - used_percent),
        resets_at=datetime.fromtimestamp(reset_at, UTC) if reset_at is not None else None,
        exhausts_at=exhausts_at,
        relief=relief,
    )


def _percent(value: float) -> float:
    return round(min(100.0, max(0.0, value)), 1)


def _hours_after(now: datetime, hours: float) -> datetime:
    # Pace offsets are measured from the pace's own clock reading; whole seconds hide that skew.
    return _aware(now + timedelta(hours=hours)).replace(microsecond=0)


def _aware(value: datetime) -> datetime:
    """Stored timestamps are naive UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
