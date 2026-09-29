from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Iterable, Mapping

from app.core.openai.models import ResponseUsage
from app.core.usage.types import UsageCostByModel, UsageCostSummary


@dataclass(frozen=True)
class ModelPrice:
    input_per_1m: float
    output_per_1m: float
    cached_input_per_1m: float | None = None
    cache_write_5m_per_1m: float | None = None
    cache_write_1h_per_1m: float | None = None
    priority_multiplier: float | None = None
    priority_input_per_1m: float | None = None
    priority_output_per_1m: float | None = None
    priority_cached_input_per_1m: float | None = None
    flex_input_per_1m: float | None = None
    flex_output_per_1m: float | None = None
    flex_cached_input_per_1m: float | None = None
    long_context_threshold_tokens: float | None = None
    long_context_input_per_1m: float | None = None
    long_context_output_per_1m: float | None = None
    long_context_cached_input_per_1m: float | None = None
    long_context_cache_write_5m_per_1m: float | None = None
    long_context_cache_write_1h_per_1m: float | None = None
    priority_long_context_input_per_1m: float | None = None
    priority_long_context_output_per_1m: float | None = None
    priority_long_context_cached_input_per_1m: float | None = None
    flex_long_context_input_per_1m: float | None = None
    flex_long_context_output_per_1m: float | None = None
    flex_long_context_cached_input_per_1m: float | None = None


@dataclass(frozen=True)
class UsageTokens:
    input_tokens: float
    output_tokens: float
    cached_input_tokens: float = 0.0


@dataclass(frozen=True)
class UsageCostBreakdown:
    input_usd: float | None
    cached_input_usd: float | None
    output_usd: float | None
    total_usd: float | None
    cache_write_usd: float | None = None


@dataclass(frozen=True)
class ClaudeUsageTokens:
    """Claude input is inclusive of cache reads and cache creation."""

    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    cache_creation_tokens: int | None = None
    cache_creation_5m_tokens: int | None = None
    cache_creation_1h_tokens: int | None = None


@dataclass(frozen=True)
class CostItem:
    model: str
    usage: UsageTokens
    service_tier: str | None = None


def _as_number(value: int | float | None) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_usage(usage: UsageTokens | ResponseUsage | None) -> UsageTokens | None:
    if isinstance(usage, UsageTokens):
        input_tokens = _as_number(usage.input_tokens)
        output_tokens = _as_number(usage.output_tokens)
        cached_tokens = _as_number(usage.cached_input_tokens)
        if input_tokens is None or output_tokens is None:
            return None
        cached_tokens = max(0.0, min(cached_tokens or 0.0, input_tokens))
        return UsageTokens(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
        )
    if not usage:
        return None
    input_tokens = _as_number(usage.input_tokens)
    output_tokens = _as_number(usage.output_tokens)
    if output_tokens is None and usage.output_tokens_details is not None:
        output_tokens = _as_number(usage.output_tokens_details.reasoning_tokens)
    if input_tokens is None or output_tokens is None:
        return None
    cached_tokens = 0.0
    if usage.input_tokens_details is not None:
        cached_tokens = _as_number(usage.input_tokens_details.cached_tokens) or 0.0
    cached_tokens = max(0.0, min(cached_tokens, input_tokens))
    return UsageTokens(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_tokens,
    )


DEFAULT_PRICING_MODELS: dict[str, ModelPrice] = {
    # Anthropic API-equivalent list rates, USD/1M. Verified against the
    # 2026-09-29 OpenCodex generated metadata snapshot (8a005dd98ff1).
    "claude-haiku-4-5": ModelPrice(1, 5, 0.1, 1.25, 2),
    "claude-sonnet-4-5": ModelPrice(3, 15, 0.3, 3.75, 6),
    "claude-sonnet-4-6": ModelPrice(3, 15, 0.3, 3.75, 6),
    "claude-opus-4-6": ModelPrice(5, 25, 0.5, 6.25, 10),
    "claude-sonnet-5": ModelPrice(2, 10, 0.2, 2.5, 4),
    "claude-opus-5": ModelPrice(5, 25, 0.5, 6.25, 10),
    "gpt-6-astra": ModelPrice(
        input_per_1m=10.0,
        cached_input_per_1m=1.0,
        output_per_1m=50.0,
        priority_input_per_1m=20.0,
        priority_cached_input_per_1m=2.0,
        priority_output_per_1m=100.0,
        flex_input_per_1m=5.0,
        flex_cached_input_per_1m=0.5,
        flex_output_per_1m=25.0,
        long_context_threshold_tokens=272_000,
        long_context_input_per_1m=20.0,
        long_context_cached_input_per_1m=2.0,
        long_context_output_per_1m=75.0,
    ),
    "gpt-5.6-sol": ModelPrice(
        input_per_1m=5.0,
        cached_input_per_1m=0.5,
        output_per_1m=30.0,
        priority_input_per_1m=10.0,
        priority_cached_input_per_1m=1.0,
        priority_output_per_1m=60.0,
        flex_input_per_1m=2.5,
        flex_cached_input_per_1m=0.25,
        flex_output_per_1m=15.0,
        long_context_threshold_tokens=272_000,
        long_context_input_per_1m=10.0,
        long_context_cached_input_per_1m=1.0,
        long_context_output_per_1m=45.0,
    ),
    "gpt-5.6-terra": ModelPrice(
        input_per_1m=2.0,
        cached_input_per_1m=0.2,
        output_per_1m=12.0,
        priority_input_per_1m=4.0,
        priority_cached_input_per_1m=0.4,
        priority_output_per_1m=24.0,
        flex_input_per_1m=1.0,
        flex_cached_input_per_1m=0.1,
        flex_output_per_1m=6.0,
        long_context_threshold_tokens=272_000,
        long_context_input_per_1m=4.0,
        long_context_cached_input_per_1m=0.4,
        long_context_output_per_1m=18.0,
    ),
    "gpt-5.6-luna": ModelPrice(
        input_per_1m=0.2,
        cached_input_per_1m=0.02,
        output_per_1m=1.2,
        priority_input_per_1m=0.4,
        priority_cached_input_per_1m=0.04,
        priority_output_per_1m=2.4,
        flex_input_per_1m=0.1,
        flex_cached_input_per_1m=0.01,
        flex_output_per_1m=0.6,
        long_context_threshold_tokens=272_000,
        long_context_input_per_1m=0.4,
        long_context_cached_input_per_1m=0.04,
        long_context_output_per_1m=1.8,
    ),
    "gpt-5.5": ModelPrice(
        input_per_1m=5.0,
        cached_input_per_1m=0.5,
        output_per_1m=30.0,
        flex_input_per_1m=2.5,
        flex_cached_input_per_1m=0.25,
        flex_output_per_1m=15.0,
        priority_input_per_1m=12.5,
        priority_cached_input_per_1m=1.25,
        priority_output_per_1m=75.0,
    ),
    "gpt-5.5-pro": ModelPrice(
        input_per_1m=30.0,
        output_per_1m=180.0,
        flex_input_per_1m=15.0,
        flex_output_per_1m=90.0,
    ),
    "gpt-5.4": ModelPrice(
        input_per_1m=2.5,
        cached_input_per_1m=0.25,
        output_per_1m=15.0,
        priority_input_per_1m=5.0,
        priority_cached_input_per_1m=0.5,
        priority_output_per_1m=30.0,
        flex_input_per_1m=1.25,
        flex_cached_input_per_1m=0.125,
        flex_output_per_1m=7.5,
        long_context_threshold_tokens=272_000,
        long_context_input_per_1m=5.0,
        long_context_cached_input_per_1m=0.5,
        long_context_output_per_1m=22.5,
    ),
    "gpt-5.4-mini": ModelPrice(
        input_per_1m=0.75,
        cached_input_per_1m=0.075,
        output_per_1m=4.5,
        flex_input_per_1m=0.375,
        flex_cached_input_per_1m=0.0375,
        flex_output_per_1m=2.25,
    ),
    "gpt-5.4-nano": ModelPrice(
        input_per_1m=0.20,
        cached_input_per_1m=0.02,
        output_per_1m=1.25,
        flex_input_per_1m=0.10,
        flex_cached_input_per_1m=0.01,
        flex_output_per_1m=0.625,
    ),
    "gpt-5.4-pro": ModelPrice(
        input_per_1m=30.0,
        output_per_1m=180.0,
        flex_input_per_1m=15.0,
        flex_output_per_1m=90.0,
        long_context_threshold_tokens=272_000,
        long_context_input_per_1m=60.0,
        long_context_output_per_1m=270.0,
    ),
    "gpt-5.3-codex": ModelPrice(
        input_per_1m=1.75,
        cached_input_per_1m=0.175,
        output_per_1m=14.0,
        priority_input_per_1m=3.5,
        priority_cached_input_per_1m=0.35,
        priority_output_per_1m=28.0,
    ),
    "gpt-5.3": ModelPrice(
        input_per_1m=1.75,
        cached_input_per_1m=0.175,
        output_per_1m=14.0,
    ),
    "gpt-5.3-chat-latest": ModelPrice(
        input_per_1m=1.75,
        cached_input_per_1m=0.175,
        output_per_1m=14.0,
    ),
    "gpt-5.2": ModelPrice(
        input_per_1m=1.75,
        cached_input_per_1m=0.175,
        output_per_1m=14.0,
        priority_multiplier=2.0,
        flex_input_per_1m=0.875,
        flex_cached_input_per_1m=0.0875,
        flex_output_per_1m=7.0,
    ),
    "gpt-5.2-chat-latest": ModelPrice(
        input_per_1m=1.75,
        cached_input_per_1m=0.175,
        output_per_1m=14.0,
    ),
    "gpt-5.1": ModelPrice(
        input_per_1m=1.25,
        cached_input_per_1m=0.125,
        output_per_1m=10.0,
        priority_multiplier=2.0,
        flex_input_per_1m=0.625,
        flex_cached_input_per_1m=0.0625,
        flex_output_per_1m=5.0,
    ),
    "gpt-5.1-chat-latest": ModelPrice(
        input_per_1m=1.25,
        cached_input_per_1m=0.125,
        output_per_1m=10.0,
    ),
    "gpt-5": ModelPrice(
        input_per_1m=1.25,
        cached_input_per_1m=0.125,
        output_per_1m=10.0,
        priority_multiplier=2.0,
        flex_input_per_1m=0.625,
        flex_cached_input_per_1m=0.0625,
        flex_output_per_1m=5.0,
    ),
    "gpt-5-chat-latest": ModelPrice(
        input_per_1m=1.25,
        cached_input_per_1m=0.125,
        output_per_1m=10.0,
    ),
    "gpt-5.2-codex": ModelPrice(
        input_per_1m=1.75,
        cached_input_per_1m=0.175,
        output_per_1m=14.0,
        priority_input_per_1m=3.5,
        priority_cached_input_per_1m=0.35,
        priority_output_per_1m=28.0,
    ),
    "gpt-5.1-codex-max": ModelPrice(
        input_per_1m=1.25,
        cached_input_per_1m=0.125,
        output_per_1m=10.0,
        priority_input_per_1m=2.5,
        priority_cached_input_per_1m=0.25,
        priority_output_per_1m=20.0,
    ),
    "gpt-5.1-codex-mini": ModelPrice(
        input_per_1m=0.25,
        cached_input_per_1m=0.025,
        output_per_1m=2.0,
    ),
    "gpt-5.1-codex": ModelPrice(
        input_per_1m=1.25,
        cached_input_per_1m=0.125,
        output_per_1m=10.0,
        priority_input_per_1m=2.5,
        priority_cached_input_per_1m=0.25,
        priority_output_per_1m=20.0,
    ),
    "gpt-5-codex": ModelPrice(
        input_per_1m=1.25,
        cached_input_per_1m=0.125,
        output_per_1m=10.0,
        priority_input_per_1m=2.5,
        priority_cached_input_per_1m=0.25,
        priority_output_per_1m=20.0,
    ),
    # OpenAI Images token-based pricing (per 1M tokens, USD).
    # gpt-image-2 (April 2026):
    #   text input  $5.00, image input $8.00, image cached input $2.00,
    #   image output $30.00.
    # The current ``ModelPrice`` shape carries a single input rate, so we
    # use the text-input rate as the dominant input cost (text dominates
    # the input side for typical prompts) and the image-output rate as
    # the output cost. Cached input maps to the image-cached rate.
    # The legacy gpt-image-1.5 / gpt-image-1 / gpt-image-1-mini entries
    # mirror gpt-image-2 today; they will be split out once OpenAI
    # publishes per-model deltas. Without these entries cost-based API
    # key quotas would resolve every /v1/images/* call to $0 and the
    # quota would never bite.
    "gpt-image-2": ModelPrice(
        input_per_1m=5.0,
        cached_input_per_1m=2.0,
        output_per_1m=30.0,
    ),
    "gpt-image-1.5": ModelPrice(
        input_per_1m=5.0,
        cached_input_per_1m=2.0,
        output_per_1m=30.0,
    ),
    "gpt-image-1": ModelPrice(
        input_per_1m=5.0,
        cached_input_per_1m=2.0,
        output_per_1m=30.0,
    ),
    "gpt-image-1-mini": ModelPrice(
        input_per_1m=5.0,
        cached_input_per_1m=2.0,
        output_per_1m=30.0,
    ),
}

DEFAULT_MODEL_ALIASES: dict[str, str] = {
    "gpt-6-astra*": "gpt-6-astra",
    "gpt-5.6": "gpt-5.6-sol",
    "gpt-5.6-sol*": "gpt-5.6-sol",
    "gpt-5.6-terra*": "gpt-5.6-terra",
    "gpt-5.6-luna*": "gpt-5.6-luna",
    "gpt-5.5-pro*": "gpt-5.5-pro",
    "gpt-5.5*": "gpt-5.5",
    "gpt-5.4-pro*": "gpt-5.4-pro",
    "gpt-5.4-mini*": "gpt-5.4-mini",
    "gpt-5.4-nano*": "gpt-5.4-nano",
    "gpt-5.4*": "gpt-5.4",
    "gpt-5.3-codex*": "gpt-5.3-codex",
    "gpt-5.3-chat-latest*": "gpt-5.3-chat-latest",
    "gpt-5.2-codex*": "gpt-5.2-codex",
    "gpt-5.2-chat-latest*": "gpt-5.2-chat-latest",
    "gpt-5.3*": "gpt-5.3",
    "gpt-5.1-chat-latest*": "gpt-5.1-chat-latest",
    "gpt-5.2*": "gpt-5.2",
    "gpt-5-chat-latest*": "gpt-5-chat-latest",
    "gpt-5.1*": "gpt-5.1",
    "gpt-5*": "gpt-5",
    "gpt-5.1-codex-max*": "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini*": "gpt-5.1-codex-mini",
    "gpt-5.1-codex*": "gpt-5.1-codex",
    "gpt-5-codex*": "gpt-5-codex",
    "gpt-image-2*": "gpt-image-2",
    "gpt-image-1.5*": "gpt-image-1.5",
    "gpt-image-1-mini*": "gpt-image-1-mini",
    "gpt-image-1*": "gpt-image-1",
}


def resolve_model_alias(model: str, aliases: Mapping[str, str]) -> str | None:
    if not model:
        return None
    normalized = model.lower()
    matched: list[tuple[int, str]] = []
    for pattern, target in aliases.items():
        if fnmatchcase(normalized, pattern.lower()):
            matched.append((len(pattern), target))
    if not matched:
        return None
    return max(matched, key=lambda item: item[0])[1]


def get_pricing_for_model(
    model: str,
    pricing: Mapping[str, ModelPrice] | None = None,
    aliases: Mapping[str, str] | None = None,
) -> tuple[str, ModelPrice] | None:
    if not model:
        return None
    if pricing is None:
        from app.core.usage.pricing_catalog import get_active_prices

        pricing = get_active_prices()
    aliases = aliases or DEFAULT_MODEL_ALIASES

    normalized = model.lower().removeprefix("anthropic/")
    for key, value in pricing.items():
        if key.lower() == normalized:
            return key, value

    claude_dated = re.fullmatch(r"(claude-(?:haiku|sonnet|opus)-\d(?:-\d)?)-\d{8}", normalized)
    if claude_dated and claude_dated[1] in pricing:
        return claude_dated[1], pricing[claude_dated[1]]

    dated = re.fullmatch(r"(.+)-\d{4}-\d{2}-\d{2}", normalized)
    if dated and dated[1] in pricing:
        return dated[1], pricing[dated[1]]

    alias = resolve_model_alias(normalized, aliases)
    if not alias or (alias == "gpt-5" and normalized.startswith("gpt-5.")):
        return None
    for key, value in pricing.items():
        if key.lower() == alias.lower():
            return key, value
    return None


def _uses_priority_tier(service_tier: str | None) -> bool:
    normalized = _normalize_service_tier(service_tier)
    if normalized is None:
        return False
    return normalized in {"priority", "fast"}


def _uses_flex_tier(service_tier: str | None) -> bool:
    normalized = _normalize_service_tier(service_tier)
    if normalized is None:
        return False
    return normalized == "flex"


def _normalize_service_tier(service_tier: str | None) -> str | None:
    if service_tier is None:
        return None
    stripped = service_tier.strip().lower()
    return stripped or None


def _effective_rates(
    usage: UsageTokens,
    price: ModelPrice,
    *,
    service_tier: str | None,
) -> tuple[float, float, float]:
    is_long_context = (
        price.long_context_threshold_tokens is not None
        and price.long_context_threshold_tokens > 0
        and usage.input_tokens > price.long_context_threshold_tokens
    )
    has_standard_long_context = (
        price.long_context_input_per_1m is not None and price.long_context_output_per_1m is not None
    )
    input_rate = price.input_per_1m
    cached_rate = price.cached_input_per_1m if price.cached_input_per_1m is not None else input_rate
    output_rate = price.output_per_1m

    if is_long_context:
        tier = "priority" if _uses_priority_tier(service_tier) else "flex" if _uses_flex_tier(service_tier) else None
        if tier is not None:
            long_input = getattr(price, f"{tier}_long_context_input_per_1m")
            long_output = getattr(price, f"{tier}_long_context_output_per_1m")
            long_cached = getattr(price, f"{tier}_long_context_cached_input_per_1m")
            if long_input is not None and long_output is not None:
                return long_input, long_cached if long_cached is not None else long_input, long_output

    if _uses_priority_tier(service_tier):
        if price.priority_input_per_1m is not None and price.priority_output_per_1m is not None:
            priority_cached = (
                price.priority_cached_input_per_1m
                if price.priority_cached_input_per_1m is not None
                else price.priority_input_per_1m
            )
            return price.priority_input_per_1m, priority_cached, price.priority_output_per_1m
        if price.priority_multiplier is not None:
            input_rate *= price.priority_multiplier
            cached_rate *= price.priority_multiplier
            output_rate *= price.priority_multiplier
            return input_rate, cached_rate, output_rate

    if _uses_flex_tier(service_tier) and price.flex_input_per_1m is not None and price.flex_output_per_1m is not None:
        input_rate = price.flex_input_per_1m
        cached_rate = price.flex_cached_input_per_1m if price.flex_cached_input_per_1m is not None else input_rate
        output_rate = price.flex_output_per_1m
        if is_long_context and has_standard_long_context:
            input_rate *= 2.0
            cached_rate *= 2.0
            output_rate *= 1.5
        return input_rate, cached_rate, output_rate

    if is_long_context and has_standard_long_context:
        assert price.long_context_input_per_1m is not None
        assert price.long_context_output_per_1m is not None
        input_rate = price.long_context_input_per_1m
        cached_rate = (
            price.long_context_cached_input_per_1m if price.long_context_cached_input_per_1m is not None else input_rate
        )
        output_rate = price.long_context_output_per_1m

    return input_rate, cached_rate, output_rate


def calculate_cost_from_usage(
    usage: UsageTokens | ResponseUsage | None,
    price: ModelPrice,
    *,
    service_tier: str | None = None,
) -> float | None:
    breakdown = calculate_cost_breakdown_from_usage(usage, price, service_tier=service_tier)
    if breakdown is None:
        return None
    return breakdown.total_usd


def calculate_cost_breakdown_from_usage(
    usage: UsageTokens | ResponseUsage | None,
    price: ModelPrice,
    *,
    service_tier: str | None = None,
    precision: int | None = None,
) -> UsageCostBreakdown | None:
    normalized = _normalize_usage(usage)
    if not normalized:
        return None
    billable_input = max(0.0, normalized.input_tokens - normalized.cached_input_tokens)

    input_rate, cached_rate, output_rate = _effective_rates(
        normalized,
        price,
        service_tier=service_tier,
    )

    input_usd = (billable_input / 1_000_000) * input_rate
    cached_input_usd = (normalized.cached_input_tokens / 1_000_000) * cached_rate
    output_usd = (normalized.output_tokens / 1_000_000) * output_rate

    if precision is not None:
        input_usd = round(input_usd, precision)
        cached_input_usd = round(cached_input_usd, precision)
        output_usd = round(output_usd, precision)

    total_usd = input_usd + cached_input_usd + output_usd

    if precision is not None:
        total_usd = round(total_usd, precision)

    return UsageCostBreakdown(
        input_usd=input_usd,
        cached_input_usd=cached_input_usd,
        output_usd=output_usd,
        total_usd=total_usd,
    )


def calculate_claude_cost_breakdown(
    usage: ClaudeUsageTokens,
    price: ModelPrice,
    *,
    precision: int | None = None,
) -> UsageCostBreakdown | None:
    """Price one Claude request using the selected whole-request context tier."""

    writes = usage.cache_creation_tokens or 0
    writes_5m = usage.cache_creation_5m_tokens or 0
    writes_1h = usage.cache_creation_1h_tokens or 0
    if (
        min(usage.input_tokens, usage.output_tokens, usage.cached_input_tokens, writes, writes_5m, writes_1h) < 0
        or (writes and (usage.cache_creation_5m_tokens is None or usage.cache_creation_1h_tokens is None))
        or writes_5m + writes_1h != writes
        or usage.cached_input_tokens + writes > usage.input_tokens
    ):
        return None
    long_context = (
        price.long_context_threshold_tokens is not None and usage.input_tokens > price.long_context_threshold_tokens
    )
    prefix = "long_context_" if long_context else ""
    input_rate = getattr(price, prefix + "input_per_1m")
    output_rate = getattr(price, prefix + "output_per_1m")
    cached_rate = getattr(price, prefix + "cached_input_per_1m")
    write_5m_rate = getattr(price, prefix + "cache_write_5m_per_1m")
    write_1h_rate = getattr(price, prefix + "cache_write_1h_per_1m")
    uncached = usage.input_tokens - usage.cached_input_tokens - writes
    if any(
        (
            uncached and input_rate is None,
            usage.cached_input_tokens and cached_rate is None,
            usage.output_tokens and output_rate is None,
            writes_5m and write_5m_rate is None,
            writes_1h and write_1h_rate is None,
        )
    ):
        return None
    input_usd = uncached * (input_rate or 0) / 1_000_000
    cached_usd = usage.cached_input_tokens * (cached_rate or 0) / 1_000_000
    write_usd = (writes_5m * (write_5m_rate or 0) + writes_1h * (write_1h_rate or 0)) / 1_000_000
    output_usd = usage.output_tokens * (output_rate or 0) / 1_000_000
    total_usd = input_usd + cached_usd + write_usd + output_usd
    if precision is not None:
        input_usd = round(input_usd, precision)
        cached_usd = round(cached_usd, precision)
        write_usd = round(write_usd, precision)
        output_usd = round(output_usd, precision)
        total_usd = round(total_usd, precision)
    return UsageCostBreakdown(input_usd, cached_usd, output_usd, total_usd, write_usd)


def calculate_costs(
    items: Iterable[CostItem],
    pricing: Mapping[str, ModelPrice] | None = None,
    aliases: Mapping[str, str] | None = None,
) -> UsageCostSummary:
    if pricing is None:
        from app.core.usage.pricing_catalog import get_active_prices

        pricing = get_active_prices()
    aliases = aliases or DEFAULT_MODEL_ALIASES

    totals: dict[str, float] = defaultdict(float)
    total_usd = 0.0

    for item in items:
        model = item.model
        usage = item.usage
        resolved = get_pricing_for_model(model, pricing, aliases)
        if not resolved:
            continue
        canonical, price = resolved
        cost = calculate_cost_from_usage(usage, price, service_tier=item.service_tier)
        if cost is None:
            continue
        totals[canonical] += cost
        total_usd += cost

    by_model = [UsageCostByModel(model=model, usd=round(value, 6)) for model, value in sorted(totals.items())]
    return UsageCostSummary(
        currency="USD",
        total_usd_7d=round(total_usd, 6),
        by_model=by_model,
    )
