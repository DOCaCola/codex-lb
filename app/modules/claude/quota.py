"""Interpret observed quotas without inventing capacity or plan entitlements."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.claude.schemas import AccountState, ModelQuota, QuotaStatus, QuotaWindow, WindowName, WindowStatus

QUOTA_FRESHNESS = timedelta(minutes=5)


def _window(name: WindowName, value: QuotaWindow | None, state: AccountState, now: datetime) -> WindowStatus:
    expired = value is not None and value.resets_at is not None and value.resets_at <= now
    unknown = value is None or state.usage_updated_at is None or expired
    stale = state.usage_error is not None or (
        state.usage_updated_at is not None and now - state.usage_updated_at >= QUOTA_FRESHNESS
    )
    return WindowStatus(
        name=name,
        utilization=value.utilization if value is not None else None,
        resets_at=value.resets_at if value is not None else None,
        freshness="unknown" if unknown else "stale" if stale else "fresh",
        exhausted=not unknown and value is not None and value.utilization >= 100,
    )


def model_quota(model: str, windows: list[WindowStatus]) -> ModelQuota:
    upstream_model = model.removeprefix("anthropic/")
    applicable: set[WindowName] = {"five_hour", "seven_day"}
    if upstream_model.startswith("claude-opus-"):
        applicable.add("seven_day_opus")
    elif upstream_model.startswith("claude-sonnet-"):
        applicable.add("seven_day_sonnet")
    blocking = [window for window in windows if window.name in applicable and window.exhausted]
    # All applicable exhausted windows must reset; never give a false deadline
    # when even one has an unknown reset time.
    deadlines = [window.resets_at for window in blocking if window.resets_at is not None]
    return ModelQuota(
        model=model,
        blocked=bool(blocking),
        blocking_windows=[window.name for window in blocking],
        retry_at=max(deadlines) if deadlines and len(deadlines) == len(blocking) else None,
    )


def quota_status(state: AccountState, *, now: datetime) -> QuotaStatus:
    usage = state.usage
    values: tuple[tuple[WindowName, QuotaWindow | None], ...] = (
        ("five_hour", usage.five_hour if usage else None),
        ("seven_day", usage.seven_day if usage else None),
        ("seven_day_opus", usage.seven_day_opus if usage else None),
        ("seven_day_sonnet", usage.seven_day_sonnet if usage else None),
    )
    windows = [_window(name, value, state, now) for name, value in values]
    return QuotaStatus(
        observed_at=state.usage_updated_at,
        windows=windows,
        models=[model_quota(selection.model, windows) for selection in state.selections],
    )
