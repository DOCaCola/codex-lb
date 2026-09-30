"""Map account-bound Reserve telemetry to additional-quota presentation, never admission."""

import math

from app.core.usage.models import LUNA_RESERVE_MODEL, ReserveUsageSnapshot, UsageWindow
from app.core.usage.refresh_policy import usage_freshness_horizon_seconds
from app.core.utils.time import naive_utc_to_epoch, to_utc_naive, utcnow
from app.db.models import Account
from app.modules.accounts.schemas import AccountAdditionalQuota, AccountAdditionalWindow


def reserve_usage_quota(account: Account) -> AccountAdditionalQuota | None:
    if account.reserve_usage is None:
        return None
    snapshot = ReserveUsageSnapshot.model_validate(account.reserve_usage)
    limit = snapshot.limit
    if limit is None:
        return None
    stale = (utcnow() - to_utc_naive(snapshot.observed_at)).total_seconds() > usage_freshness_horizon_seconds()
    rate_limit = limit.rate_limit
    availability = "unknown"
    if not stale and rate_limit is not None:
        if (
            rate_limit.allowed is False
            or snapshot.ordinary_allowed is True
            or (snapshot.banner_type is not None and snapshot.banner_type != "luna_reserve")
        ):
            availability = "unavailable"
        elif (
            rate_limit.allowed is True and snapshot.ordinary_allowed is False and snapshot.banner_type == "luna_reserve"
        ):
            availability = "available"
    observed_epoch = naive_utc_to_epoch(to_utc_naive(snapshot.observed_at))
    return AccountAdditionalQuota(
        quota_key="gpt_reserve",
        limit_name=LUNA_RESERVE_MODEL,
        metered_feature=limit.metered_feature,
        display_label="Luna Reserve",
        routing_policy=None,
        availability=availability,
        primary_window=_window(rate_limit.primary_window, observed_epoch) if rate_limit and not stale else None,
        secondary_window=_window(rate_limit.secondary_window, observed_epoch) if rate_limit and not stale else None,
    )


def _window(window: UsageWindow | None, observed_epoch: int) -> AccountAdditionalWindow | None:
    if window is None:
        return None
    reset_at = window.reset_at
    if reset_at is None and window.reset_after_seconds is not None:
        reset_at = observed_epoch + window.reset_after_seconds
    used_percent = window.used_percent
    if used_percent is not None and not math.isfinite(used_percent):
        used_percent = None
    return AccountAdditionalWindow(
        used_percent=used_percent,
        reset_at=reset_at,
        window_minutes=window.limit_window_seconds // 60 if window.limit_window_seconds is not None else None,
    )
