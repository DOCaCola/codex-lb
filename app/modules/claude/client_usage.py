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
from app.modules.claude.subscription import quota_weight, subscription_plan

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

    def headers(self, label: str, window_minutes: int) -> dict[str, str]:
        if self.capacity <= 0:
            return {}
        headers = {
            f"x-codex-{label}-used-percent": str(self.used / self.capacity * 100.0),
            f"x-codex-{label}-window-minutes": str(window_minutes),
        }
        if self.resets:
            headers[f"x-codex-{label}-reset-at"] = str(min(self.resets))
        return headers


def claude_pool_rate_limit_headers(
    accounts: Sequence[ClaudeAccount],
    *,
    windows: Collection[WindowName],
    now: datetime,
) -> dict[str, str]:
    """Encode the enabled, plan-weighted Claude pool as ``x-codex-*`` headers."""

    five_hour = _PoolWindow()
    weekly = _PoolWindow()
    for account in accounts:
        if not account.source.is_enabled:
            continue
        state = AccountState.model_validate_json(account.state_json)
        weight = quota_weight(subscription_plan(state.subscription))
        if weight is None:
            continue
        statuses = {status.name: status for status in quota_status(state, now=now).windows if status.name in windows}
        if all(_known_utilization(status) is None for status in statuses.values()):
            continue
        exhausted = any(status.exhausted for status in statuses.values())
        weekly_windows = [
            status
            for name, status in statuses.items()
            if name != "five_hour" and _known_utilization(status) is not None
        ]
        five_hour.add(weight, statuses.get("five_hour"), exhausted=exhausted)
        binding_weekly = max(weekly_windows, key=lambda status: status.utilization or 0.0) if weekly_windows else None
        weekly.add(weight, binding_weekly, exhausted=exhausted)
    return {
        **five_hour.headers("primary", _FIVE_HOUR_WINDOW_MINUTES),
        **weekly.headers("secondary", _SEVEN_DAY_WINDOW_MINUTES),
    }


async def load_claude_pool_rate_limit_headers(windows: Collection[WindowName]) -> dict[str, str]:
    async with get_background_session() as session:
        accounts = await ClaudeRepository(session).list_accounts()
        return claude_pool_rate_limit_headers(accounts, windows=windows, now=datetime.now(UTC))


def _known_utilization(window: WindowStatus | None) -> float | None:
    if window is None or window.freshness == "unknown":
        return None
    return window.utilization
