"""Subscription labels from provider metadata; never quota or entitlement guesses."""

from app.modules.claude.schemas import ClaudePlanType, SubscriptionMetadata

_PLANS: dict[str, ClaudePlanType] = {
    "free": "free",
    "pro": "pro",
    "max": "max",
    "max_5x": "max_5x",
    "max_20x": "max_20x",
    "team": "team",
    "enterprise": "enterprise",
}


def _known_plan(value: str | None) -> ClaudePlanType | None:
    if value is None:
        return None
    identifier = value.strip().lower().removeprefix("default_").removeprefix("claude_")
    return _PLANS.get(identifier)


def subscription_plan(metadata: SubscriptionMetadata | None) -> ClaudePlanType:
    if metadata is None:
        return "unknown"
    return _known_plan(metadata.rate_limit_tier) or _known_plan(metadata.subscription_type) or "unknown"


# Subscription quota relative to Pro, for pooling plan windows into one display
# unit (agent-lb's tier weights; Anthropic sells Max as 5x/20x Pro usage). Plans
# without a stated multiplier are not pooled. Display only; routing is unaffected.
_QUOTA_WEIGHTS: dict[ClaudePlanType, int] = {"pro": 1, "max_5x": 5, "max_20x": 20}


def quota_weight(plan: ClaudePlanType) -> int | None:
    return _QUOTA_WEIGHTS.get(plan)
