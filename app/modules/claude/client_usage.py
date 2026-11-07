"""Claude subscription pool usage reported to Codex clients.

Accounts are weighted in Pro units like the Claude weekly pace. The pool's
weekly figure takes, per account, the most-used weekly window that applies to
the served model, because that window binds.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.db.models import ClaudeAccount
from app.db.session import get_background_session
from app.modules.claude.quota import quota_status
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import AccountState, WindowName, WindowStatus
from app.modules.claude.subscription import quota_weights, subscription_plan

BASE_WINDOWS: frozenset[WindowName] = frozenset({"five_hour", "seven_day"})
_FIVE_HOUR_WINDOW_MINUTES = 300
_SEVEN_DAY_WINDOW_MINUTES = 10_080


@dataclass
class _PoolWindow:
    capacity: float = 0.0
    used: float = 0.0
    resets: list[int] = field(default_factory=list)

    def add(self, weight: int, window: WindowStatus | None, *, exhausted: bool) -> None:
        utilization = _known_utilization(window)
        self.capacity += weight
        self.used += weight * (100.0 if exhausted else utilization or 0.0) / 100.0
        if window is not None and utilization and window.resets_at is not None:
            self.resets.append(int(window.resets_at.timestamp()))

    def summary(self) -> ClaudePoolWindow | None:
        if self.capacity <= 0:
            return None
        return ClaudePoolWindow(
            used_percent=self.used / self.capacity * 100.0,
            reset_at=min(self.resets) if self.resets else None,
        )


@dataclass(frozen=True)
class ClaudePoolWindow:
    used_percent: float
    # Epoch seconds of the soonest reset of an account with usage in the window.
    reset_at: int | None


@dataclass(frozen=True)
class ClaudePool:
    """The enabled, plan-weighted Claude pool; an exhausted account counts as fully used in every window."""

    five_hour: ClaudePoolWindow | None
    weekly: ClaudePoolWindow | None
    account_count: int
    ready_account_count: int
    observed_at: datetime | None
    stale: bool


def summarize_claude_pool(
    accounts: Sequence[ClaudeAccount],
    *,
    windows: Collection[WindowName],
    now: datetime,
) -> ClaudePool:
    five_hour = _PoolWindow()
    weekly = _PoolWindow()
    account_count = 0
    ready_account_count = 0
    observed: list[datetime] = []
    stale = False
    for account in accounts:
        if not account.source.is_enabled:
            continue
        state = AccountState.model_validate_json(account.state_json)
        weights = quota_weights(subscription_plan(state.subscription))
        if weights is None:
            continue
        statuses = {status.name: status for status in quota_status(state, now=now).windows if status.name in windows}
        if all(_known_utilization(status) is None for status in statuses.values()):
            continue
        exhausted = any(status.exhausted for status in statuses.values())
        account_count += 1
        ready_account_count += not exhausted
        observed.extend(status.observed_at for status in statuses.values() if status.observed_at is not None)
        stale = stale or any(status.freshness == "stale" for status in statuses.values())
        weekly_windows = [
            status
            for name, status in statuses.items()
            if name != "five_hour" and _known_utilization(status) is not None
        ]
        five_hour.add(weights.five_hour, statuses.get("five_hour"), exhausted=exhausted)
        binding_weekly = max(weekly_windows, key=lambda status: status.utilization or 0.0) if weekly_windows else None
        weekly.add(weights.weekly, binding_weekly, exhausted=exhausted)
    return ClaudePool(
        five_hour=five_hour.summary(),
        weekly=weekly.summary(),
        account_count=account_count,
        ready_account_count=ready_account_count,
        observed_at=max(observed, default=None),
        stale=stale,
    )


def claude_pool_rate_limit_headers(
    accounts: Sequence[ClaudeAccount],
    *,
    windows: Collection[WindowName],
    now: datetime,
) -> dict[str, str]:
    """Encode the enabled, plan-weighted Claude pool as ``x-codex-*`` headers."""

    pool = summarize_claude_pool(accounts, windows=windows, now=now)
    return {
        **_window_headers("primary", pool.five_hour, _FIVE_HOUR_WINDOW_MINUTES),
        **_window_headers("secondary", pool.weekly, _SEVEN_DAY_WINDOW_MINUTES),
    }


def _window_headers(label: str, window: ClaudePoolWindow | None, window_minutes: int) -> dict[str, str]:
    if window is None:
        return {}
    headers = {
        f"x-codex-{label}-used-percent": str(window.used_percent),
        f"x-codex-{label}-window-minutes": str(window_minutes),
    }
    if window.reset_at is not None:
        headers[f"x-codex-{label}-reset-at"] = str(window.reset_at)
    return headers


async def load_claude_pool_rate_limit_headers(windows: Collection[WindowName]) -> dict[str, str]:
    async with get_background_session() as session:
        accounts = await ClaudeRepository(session).list_accounts()
        return claude_pool_rate_limit_headers(accounts, windows=windows, now=datetime.now(UTC))


def _known_utilization(window: WindowStatus | None) -> float | None:
    if window is None or window.freshness == "unknown":
        return None
    return window.utilization
