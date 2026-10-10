from __future__ import annotations

from typing import Protocol

from app.core.usage.pricing import (
    ClaudeUsageTokens,
    UsageCostBreakdown,
    UsageTokens,
    calculate_claude_cost_breakdown,
    calculate_cost_breakdown_from_usage,
    calculate_cost_from_usage,
    get_pricing_for_model,
)

# Request-log status classification shared by every error-metric surface
# (usage builders, time rollups, reports, fleet): `cancelled` is a normal
# client-side terminal (written when the downstream client disconnects before
# the final event lands — routing health already treats it as non-penalizing),
# so only statuses outside this tuple count as errors.
SUCCESS_STATUS = "success"
CANCELLED_STATUS = "cancelled"
NON_ERROR_STATUSES: tuple[str, ...] = (SUCCESS_STATUS, CANCELLED_STATUS)
# The error code cancelled rows carry; excluded read-side from historical
# error-satellite rollup rows that were folded under the legacy
# `status != 'success'` filter.
CLIENT_DISCONNECT_ERROR_CODE = "client_disconnected"
# Upstream's 60-minute Responses websocket lifetime cap. The client opens a new
# connection and resends the turn, so the refused attempt is a superseded
# terminal like a disconnect: stored as cancelled and shown as a reconnect.
WEBSOCKET_CONNECTION_LIMIT_ERROR_CODE = "websocket_connection_limit_reached"
# A Responses turn the client stopped with ``response.interrupt``. It ends with
# ``response.incomplete`` (reason ``interrupted``), is stored as cancelled and
# still anchors the client's follow-up like a completed turn.
CLIENT_INTERRUPT_ERROR_CODE = "interrupted"


class RequestLogLike(Protocol):
    @property
    def model_source_kind(self) -> str | None: ...

    @property
    def model(self) -> str | None: ...

    @property
    def service_tier(self) -> str | None: ...

    @property
    def input_tokens(self) -> int | None: ...

    @property
    def output_tokens(self) -> int | None: ...

    @property
    def cached_input_tokens(self) -> int | None: ...

    @property
    def cache_creation_tokens(self) -> int | None: ...

    @property
    def cache_creation_5m_tokens(self) -> int | None: ...

    @property
    def cache_creation_1h_tokens(self) -> int | None: ...

    @property
    def reasoning_tokens(self) -> int | None: ...

    @property
    def cost_usd(self) -> float | None: ...

    @property
    def cost_provenance(self) -> str | None: ...


def cached_input_tokens_from_log(log: RequestLogLike) -> int | None:
    cached_tokens = log.cached_input_tokens
    if cached_tokens is None:
        return None
    cached_tokens = max(0, int(cached_tokens))
    input_tokens = log.input_tokens
    if input_tokens is not None:
        cached_tokens = min(cached_tokens, int(input_tokens))
    return cached_tokens


def usage_tokens_from_log(log: RequestLogLike) -> UsageTokens | None:
    input_tokens = log.input_tokens
    if input_tokens is None:
        return None
    output_tokens = output_tokens_from_log(log)
    if output_tokens is None:
        return None
    cached_tokens = cached_input_tokens_from_log(log) or 0
    return UsageTokens(
        input_tokens=float(input_tokens),
        output_tokens=float(output_tokens),
        cached_input_tokens=float(cached_tokens),
    )


def output_tokens_from_log(log: RequestLogLike) -> int | None:
    output_tokens = log.output_tokens
    if output_tokens is not None:
        return int(output_tokens)
    reasoning_tokens = log.reasoning_tokens
    if reasoning_tokens is None:
        return None
    return int(reasoning_tokens)


def calculated_cost_from_log(log: RequestLogLike, *, precision: int | None = None) -> float | None:
    if not log.model:
        return None
    if log.model_source_kind == "claude":
        # Historical Claude rows lack cache-write detail. Only the dispatch's
        # persisted estimate may price a Claude request; never backfill a guess.
        return None
    usage = usage_tokens_from_log(log)
    if not usage:
        return None
    resolved = get_pricing_for_model(log.model, None, None)
    if not resolved:
        return None
    _, price = resolved
    cost = calculate_cost_from_usage(usage, price, service_tier=log.service_tier)
    if cost is None:
        return None
    if precision is None:
        return cost
    return round(cost, precision)


def cost_from_log(log: RequestLogLike, *, precision: int | None = None) -> float | None:
    if log.model_source_kind == "claude" and log.cost_provenance is None and log.cost_usd == 0:
        return None
    cost = log.cost_usd
    if cost is None:
        return None
    if precision is None:
        return float(cost)
    return round(float(cost), precision)


def _totals_match(left: float | None, right: float | None, *, precision: int | None) -> bool:
    if left is None or right is None:
        return False
    if precision is None:
        return left == right
    return abs(left - right) < (10 ** (-precision)) / 2


def cost_breakdown_from_log(log: RequestLogLike, *, precision: int | None = None) -> UsageCostBreakdown:
    if log.model_source_kind == "claude":
        return _claude_cost_breakdown_from_log(log, precision=precision)
    full_breakdown: UsageCostBreakdown | None = None
    input_usd: float | None = None
    cached_input_usd: float | None = None
    output_usd: float | None = None
    raw_total_usd: float | None = None
    total_usd: float | None = None
    if log.model:
        resolved = get_pricing_for_model(log.model, None, None)
        if resolved is not None:
            _, price = resolved
            input_tokens = log.input_tokens
            cached_tokens = cached_input_tokens_from_log(log)
            output_tokens = output_tokens_from_log(log)
            usage = usage_tokens_from_log(log)
            if usage is not None:
                raw_full_breakdown = calculate_cost_breakdown_from_usage(usage, price, service_tier=log.service_tier)
                if raw_full_breakdown is not None:
                    raw_total_usd = raw_full_breakdown.total_usd
                full_breakdown = calculate_cost_breakdown_from_usage(
                    usage,
                    price,
                    service_tier=log.service_tier,
                    precision=precision,
                )
                if full_breakdown is not None:
                    total_usd = full_breakdown.total_usd
            if input_tokens is not None and cached_tokens is not None:
                input_breakdown = calculate_cost_breakdown_from_usage(
                    UsageTokens(
                        input_tokens=float(input_tokens),
                        output_tokens=0.0,
                        cached_input_tokens=float(cached_tokens),
                    ),
                    price,
                    service_tier=log.service_tier,
                    precision=precision,
                )
                if input_breakdown is not None:
                    input_usd = input_breakdown.input_usd
                    cached_input_usd = input_breakdown.cached_input_usd
            if output_tokens is not None:
                output_breakdown = calculate_cost_breakdown_from_usage(
                    UsageTokens(
                        input_tokens=float(input_tokens or 0),
                        output_tokens=float(output_tokens),
                        cached_input_tokens=float(cached_tokens or 0),
                    ),
                    price,
                    service_tier=log.service_tier,
                    precision=precision,
                )
                if output_breakdown is not None:
                    output_usd = output_breakdown.output_usd

    persisted_cost = cost_from_log(log, precision=precision)
    if persisted_cost is not None:
        persisted_raw_cost = cost_from_log(log)
        if not _totals_match(persisted_raw_cost, raw_total_usd, precision=precision):
            return UsageCostBreakdown(
                input_usd=None,
                cached_input_usd=None,
                output_usd=None,
                total_usd=persisted_cost,
            )
        return UsageCostBreakdown(
            input_usd=input_usd,
            cached_input_usd=cached_input_usd,
            output_usd=output_usd,
            total_usd=persisted_cost,
        )
    if full_breakdown is not None:
        return UsageCostBreakdown(
            input_usd=input_usd,
            cached_input_usd=cached_input_usd,
            output_usd=output_usd,
            total_usd=total_usd,
        )
    return UsageCostBreakdown(
        input_usd=input_usd,
        cached_input_usd=cached_input_usd,
        output_usd=output_usd,
        total_usd=None,
    )


def _claude_cost_breakdown_from_log(log: RequestLogLike, *, precision: int | None) -> UsageCostBreakdown:
    total = cost_from_log(log, precision=precision)
    unknown_parts = UsageCostBreakdown(None, None, None, total)
    if total is None or log.model is None:
        return unknown_parts
    if (
        log.input_tokens is None
        or log.output_tokens is None
        or log.cached_input_tokens is None
        or log.cache_creation_tokens is None
        or log.cache_creation_5m_tokens is None
        or log.cache_creation_1h_tokens is None
    ):
        return unknown_parts
    resolved = get_pricing_for_model(log.model)
    if resolved is None:
        return unknown_parts
    breakdown = calculate_claude_cost_breakdown(
        ClaudeUsageTokens(
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            cached_input_tokens=log.cached_input_tokens,
            cache_creation_tokens=log.cache_creation_tokens,
            cache_creation_5m_tokens=log.cache_creation_5m_tokens,
            cache_creation_1h_tokens=log.cache_creation_1h_tokens,
        ),
        resolved[1],
    )
    if breakdown is None or not _totals_match(cost_from_log(log), breakdown.total_usd, precision=6):
        return unknown_parts
    if precision is not None:
        breakdown = calculate_claude_cost_breakdown(
            ClaudeUsageTokens(
                input_tokens=log.input_tokens,
                output_tokens=log.output_tokens,
                cached_input_tokens=log.cached_input_tokens,
                cache_creation_tokens=log.cache_creation_tokens,
                cache_creation_5m_tokens=log.cache_creation_5m_tokens,
                cache_creation_1h_tokens=log.cache_creation_1h_tokens,
            ),
            resolved[1],
            precision=precision,
        )
        assert breakdown is not None
    return UsageCostBreakdown(
        input_usd=breakdown.input_usd,
        cached_input_usd=breakdown.cached_input_usd,
        output_usd=breakdown.output_usd,
        total_usd=total,
        cache_write_usd=breakdown.cache_write_usd,
    )


def total_tokens_from_log(log: RequestLogLike) -> int | None:
    input_tokens = log.input_tokens
    output_tokens = output_tokens_from_log(log)
    if input_tokens is None and output_tokens is None:
        return None
    return (input_tokens or 0) + (output_tokens or 0)
