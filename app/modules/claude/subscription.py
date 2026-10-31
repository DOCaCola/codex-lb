"""Subscription labels from provider metadata; never quota or entitlement guesses."""

from app.modules.claude.schemas import ClaudePlanType, QuotaWeights, SubscriptionMetadata

# Anthropic renamed Max 5x to Max and Max 20x to Ultra on 2026-10-30. Rate-limit
# tiers name the plan under either scheme.
_TIER_PLANS: dict[str, ClaudePlanType] = {
    "free": "free",
    "pro": "pro",
    "max": "max",
    "max_5x": "max",
    "ultra": "ultra",
    "max_20x": "ultra",
    "team": "team",
    "enterprise": "enterprise",
}

# A bare "max" subscription type named both Max tiers before the rename, so it
# cannot identify a plan without its rate-limit tier.
_SUBSCRIPTION_PLANS: dict[str, ClaudePlanType] = {
    "free": "free",
    "pro": "pro",
    "ultra": "ultra",
    "team": "team",
    "enterprise": "enterprise",
}


def _identifier(value: str) -> str:
    return value.strip().lower().removeprefix("default_").removeprefix("claude_")


def subscription_plan(metadata: SubscriptionMetadata | None) -> ClaudePlanType:
    if metadata is None:
        return "unknown"
    if metadata.rate_limit_tier is not None and (plan := _TIER_PLANS.get(_identifier(metadata.rate_limit_tier))):
        return plan
    if metadata.subscription_type is not None:
        return _SUBSCRIPTION_PLANS.get(_identifier(metadata.subscription_type), "unknown")
    return "unknown"


# Published limits relative to Pro. Ultra's weekly limit is 10x Pro; its "20x"
# only ever described the five-hour limit. Plans without a published multiplier
# are not pooled. Display only; routing is unaffected.
_QUOTA_WEIGHTS: dict[ClaudePlanType, QuotaWeights] = {
    "pro": QuotaWeights(five_hour=1, weekly=1),
    "max": QuotaWeights(five_hour=5, weekly=5),
    "ultra": QuotaWeights(five_hour=20, weekly=10),
}


def quota_weights(plan: ClaudePlanType) -> QuotaWeights | None:
    return _QUOTA_WEIGHTS.get(plan)
