"""Family quota windows from retrieveUserQuotaSummary; plan and Pro-unit weights from the tier.

Each family (Gemini, Gemini 4 Argon, Claude & GPT) has its own 5-hour and weekly windows. Values are
fractions only. A family is blocked when either reported window is spent; the binding window is the
one with less remaining (OmniRoute quotaCache.ts). Readings whose reset has passed are stale and are
never used as exhaustion evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.types import JsonValue
from app.modules.antigravity.catalog import quota_family
from app.modules.antigravity.schemas import (
    AccountState,
    PlanType,
    QuotaBucket,
    QuotaFamily,
    QuotaWindowName,
    Subscription,
    WindowStatus,
)

# Google publishes Ultra as 5x and 20x Pro; free plans are not weighted until their size is known.
PLAN_WEIGHTS: dict[PlanType, int] = {"pro": 1, "ultra_5x": 5, "ultra_20x": 20}
_FIVE_HOUR = re.compile(r"\b5h\b|five[-\s]?hour|\bsession\b", re.IGNORECASE)
_WEEKLY = re.compile(r"\bweekly\b|\b7d\b|seven[-\s]?day", re.IGNORECASE)
_ARGON_BUCKET = re.compile(r"\bargon\b|gemini-argon", re.IGNORECASE)


def _window(bucket: dict[str, JsonValue]) -> QuotaWindowName | None:
    explicit = str(bucket.get("window") or "").strip().lower()
    if explicit in ("5h", "session"):
        return "five_hour"
    if explicit in ("weekly", "7d"):
        return "weekly"
    text = f"{bucket.get('bucketId') or ''} {bucket.get('displayName') or ''}"
    if _FIVE_HOUR.search(text):
        return "five_hour"
    if _WEEKLY.search(text):
        return "weekly"
    return None


def _reset(value: JsonValue) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def parse_summary(data: dict[str, JsonValue]) -> list[QuotaBucket]:
    groups = data.get("groups")
    if not isinstance(groups, list):
        nested = data.get("quotaSummary")
        groups = nested.get("groups") if isinstance(nested, dict) else None
    buckets: dict[tuple[QuotaFamily, QuotaWindowName], QuotaBucket] = {}
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, dict):
            continue
        group_text = f"{group.get('groupId') or group.get('id') or ''} {group.get('displayName') or ''}"
        raw_buckets = group.get("buckets")
        for bucket in raw_buckets if isinstance(raw_buckets, list) else []:
            if not isinstance(bucket, dict) or bucket.get("disabled") is True:
                continue
            window = _window(bucket)
            if window is None:
                continue
            bucket_text = f"{bucket.get('bucketId') or ''} {bucket.get('displayName') or ''}"
            # A bucket names its own family before its group does (opencodex).
            family: QuotaFamily = "argon" if _ARGON_BUCKET.search(bucket_text) else quota_family(group_text, None)
            remaining = bucket.get("remaining")
            source = remaining if isinstance(remaining, dict) else bucket
            fraction = source.get("remainingFraction")
            if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or fraction < 0:
                continue
            buckets.setdefault(
                (family, window),
                QuotaBucket(
                    family=family,
                    window=window,
                    remaining_fraction=min(1.0, float(fraction)),
                    resets_at=_reset(source.get("resetTime")),
                ),
            )
    return list(buckets.values())


def plan_type(subscription: Subscription | None) -> PlanType:
    if subscription is None:
        return "unknown"
    tier = subscription.paid_tier.id if subscription.paid_tier else None
    if tier is None:
        current = subscription.current_tier.id if subscription.current_tier else ""
        return "free" if current in ("free-tier", "standard-tier", "legacy-tier") else "unknown"
    if tier.startswith("g1-pro"):
        return "pro"
    if tier.startswith("g1-ultra-lite"):
        return "ultra_5x"
    if tier.startswith("g1-ultra"):
        return "ultra_20x"
    return "unknown"


def quota_weight(plan: PlanType) -> int | None:
    return PLAN_WEIGHTS.get(plan)


def current_buckets(state: AccountState, now: datetime) -> list[QuotaBucket]:
    """Readings still inside their window; a passed reset invalidates the reading."""
    return [bucket for bucket in state.quota if bucket.resets_at is None or bucket.resets_at > now]


def window_status(state: AccountState, now: datetime) -> list[WindowStatus]:
    return [
        WindowStatus(
            family=bucket.family,
            window=bucket.window,
            used_percent=bucket.used_percent,
            resets_at=bucket.resets_at,
            exhausted=bucket.remaining_fraction <= 0,
        )
        for bucket in current_buckets(state, now)
    ]


@dataclass(frozen=True)
class FamilyQuota:
    blocked: bool
    retry_at: datetime | None
    # The window with less remaining, which drives quota-ranked routing.
    binding: QuotaBucket | None
    five_hour: QuotaBucket | None
    weekly: QuotaBucket | None


def family_quota(state: AccountState, family: QuotaFamily, now: datetime) -> FamilyQuota:
    readings = {bucket.window: bucket for bucket in current_buckets(state, now) if bucket.family == family}
    spent = [bucket for bucket in readings.values() if bucket.remaining_fraction <= 0]
    binding = min(readings.values(), key=lambda bucket: bucket.remaining_fraction, default=None)
    resets = [bucket.resets_at for bucket in spent if bucket.resets_at is not None]
    return FamilyQuota(
        blocked=bool(spent),
        retry_at=max(resets) if spent and len(resets) == len(spent) else None,
        binding=binding,
        five_hour=readings.get("five_hour"),
        weekly=readings.get("weekly"),
    )
