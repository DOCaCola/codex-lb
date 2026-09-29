from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone

from app.core import usage as usage_core
from app.core.usage.coverage import CostCoverage
from app.core.usage.logs import (
    CANCELLED_STATUS,
    NON_ERROR_STATUSES,
    cached_input_tokens_from_log,
    total_tokens_from_log,
)
from app.core.usage.types import (
    BucketConversationAggregate,
    BucketModelAggregate,
    RequestActivityAggregate,
    UsageCostByModel,
    UsageCostSummary,
    UsageMetricsSummary,
    UsageSummaryLogsAggregate,
    UsageSummaryPayload,
    UsageWindowRow,
    UsageWindowSnapshot,
)
from app.core.utils.time import from_epoch_seconds
from app.db.models import Account, AdditionalUsageHistory, RequestLog
from app.modules.shared.schemas import RequestCostCoverage
from app.modules.usage.schemas import (
    MetricsTrends,
    TrendPoint,
    UsageCost,
    UsageHistoryItem,
    UsageHistoryResponse,
    UsageMetrics,
    UsageSummaryResponse,
    UsageWindow,
    UsageWindowResponse,
)

_BUCKET_COUNT = 28
_BUCKET_SECONDS = 21600  # 6 hours


@dataclass(frozen=True)
class ActivityCostSummary:
    currency: str
    total_usd: float
    by_model: list[UsageCostByModel]
    cost_coverage: CostCoverage = field(default_factory=CostCoverage)


def cost_coverage_response(coverage: CostCoverage) -> RequestCostCoverage:
    # Rounded like the sibling ``total_usd`` so the two never disagree in JSON.
    return RequestCostCoverage(**asdict(replace(coverage, known_cost_usd=round(coverage.known_cost_usd, 6))))


@dataclass(frozen=True)
class ActivityMetricsSummary:
    requests: int | None
    tokens: int | None
    cached_input_tokens: int | None = None
    error_rate: float | None = None
    error_count: int | None = None
    cancelled_count: int | None = None
    top_error: str | None = None
    conversation_count: int = 0
    conversation_request_count: int = 0


def align_bucket_window_start(
    since: datetime,
    bucket_seconds: int,
) -> datetime:
    since_epoch = (
        int(since.replace(tzinfo=timezone.utc).timestamp()) if since.tzinfo is None else int(since.timestamp())
    )
    remainder = since_epoch % bucket_seconds
    first_bucket_epoch = since_epoch if remainder == 0 else since_epoch - remainder + bucket_seconds
    aligned = datetime.fromtimestamp(first_bucket_epoch, tz=timezone.utc)
    if since.tzinfo is None:
        return aligned.replace(tzinfo=None)
    return aligned


def build_trends_from_buckets(
    rows: list[BucketModelAggregate],
    since: datetime,
    bucket_seconds: int = _BUCKET_SECONDS,
    bucket_count: int = _BUCKET_COUNT,
    top_error: str | None = None,
    conversation_rows: list[BucketConversationAggregate] | None = None,
) -> tuple[MetricsTrends, ActivityMetricsSummary, ActivityCostSummary]:
    # Align slots so the last slot contains "now" (since + window).
    # Use floor to snap since to a bucket boundary, then shift by 1
    # so that recent data falls within the slot range.
    first_bucket = align_bucket_window_start(since, bucket_seconds)
    first_bucket_epoch = (
        int(first_bucket.replace(tzinfo=timezone.utc).timestamp())
        if first_bucket.tzinfo is None
        else int(first_bucket.timestamp())
    )
    slots = [first_bucket_epoch + i * bucket_seconds for i in range(bucket_count)]
    slot_set = set(slots)

    # Accumulate per-bucket values
    bucket_requests: dict[int, int] = defaultdict(int)
    bucket_errors: dict[int, int] = defaultdict(int)
    bucket_tokens: dict[int, int] = defaultdict(int)
    bucket_costs: dict[int, CostCoverage] = defaultdict(CostCoverage)
    bucket_conversations: dict[int, int] = defaultdict(int)
    total_costs_by_model: dict[str, CostCoverage] = defaultdict(CostCoverage)

    total_requests = 0
    total_errors = 0
    total_cancelled = 0
    total_tokens = 0
    total_cached_tokens = 0
    total_cost = CostCoverage()

    for row in rows:
        epoch = row.bucket_epoch
        if epoch not in slot_set:
            continue
        bucket_requests[epoch] += row.request_count
        bucket_errors[epoch] += row.error_count
        bucket_tokens[epoch] += row.input_tokens + row.output_tokens
        bucket_costs[epoch] += row.cost_coverage
        total_costs_by_model[row.model] += row.cost_coverage

        total_requests += row.request_count
        total_errors += row.error_count
        total_cancelled += row.cancelled_count
        total_tokens += row.input_tokens + row.output_tokens
        total_cached_tokens += row.cached_input_tokens
        total_cost += row.cost_coverage

    for row in conversation_rows or []:
        if row.bucket_epoch in slot_set:
            bucket_conversations[row.bucket_epoch] += row.conversation_count

    requests_points: list[TrendPoint] = []
    tokens_points: list[TrendPoint] = []
    cost_points: list[TrendPoint] = []
    error_rate_points: list[TrendPoint] = []
    conversations_points: list[TrendPoint] = []

    for epoch in slots:
        t = datetime.fromtimestamp(epoch, tz=timezone.utc)
        req = bucket_requests.get(epoch, 0)
        err = bucket_errors.get(epoch, 0)
        tok = bucket_tokens.get(epoch, 0)
        cost_value = bucket_costs.get(epoch, CostCoverage())
        conversations = bucket_conversations.get(epoch, 0)

        err_rate = (err / req) if req > 0 else 0.0

        requests_points.append(TrendPoint(t=t, v=float(req)))
        tokens_points.append(TrendPoint(t=t, v=float(tok)))
        cost_points.append(
            TrendPoint(t=t, v=round(cost_value.known_cost_usd, 6), coverage=cost_coverage_response(cost_value))
        )
        error_rate_points.append(TrendPoint(t=t, v=round(err_rate, 4)))
        conversations_points.append(TrendPoint(t=t, v=float(conversations)))

    trends = MetricsTrends(
        requests=requests_points,
        tokens=tokens_points,
        cost=cost_points,
        error_rate=error_rate_points,
        conversations=conversations_points,
    )

    error_rate_total: float | None = None
    if total_requests > 0:
        error_rate_total = total_errors / total_requests

    metrics = ActivityMetricsSummary(
        requests=total_requests,
        tokens=total_tokens,
        cached_input_tokens=total_cached_tokens,
        error_rate=error_rate_total,
        error_count=total_errors,
        cancelled_count=total_cancelled,
        top_error=top_error,
    )

    cost_summary = ActivityCostSummary(
        currency="USD",
        total_usd=round(total_cost.known_cost_usd, 6),
        by_model=[
            UsageCostByModel(model=model, usd=round(cost.known_cost_usd, 6))
            for model, cost in sorted(total_costs_by_model.items())
            if cost.priced_requests > 0
        ],
        cost_coverage=total_cost,
    )

    return trends, metrics, cost_summary


def build_activity_summaries(
    aggregate: RequestActivityAggregate,
    *,
    top_error: str | None = None,
) -> tuple[ActivityMetricsSummary, ActivityCostSummary]:
    total_requests = aggregate.request_count
    total_tokens = aggregate.input_tokens + aggregate.output_tokens
    error_rate: float | None = None
    if total_requests > 0:
        error_rate = aggregate.error_count / total_requests

    return (
        ActivityMetricsSummary(
            requests=total_requests,
            tokens=total_tokens,
            cached_input_tokens=aggregate.cached_input_tokens,
            error_rate=error_rate,
            error_count=aggregate.error_count,
            cancelled_count=aggregate.cancelled_count,
            top_error=top_error,
            conversation_count=aggregate.conversation_count,
            conversation_request_count=aggregate.conversation_request_count,
        ),
        ActivityCostSummary(
            currency="USD",
            total_usd=round(aggregate.cost_coverage.known_cost_usd, 6),
            by_model=[],
            cost_coverage=aggregate.cost_coverage,
        ),
    )


def build_usage_summary_response(
    *,
    accounts: list[Account],
    primary_rows: list[UsageWindowRow],
    secondary_rows: list[UsageWindowRow],
    monthly_rows: list[UsageWindowRow],
    logs_secondary: list[RequestLog],
    cost: UsageCostSummary,
    metrics_override: UsageMetricsSummary | None = None,
) -> UsageSummaryResponse:
    account_map = {account.id: account for account in accounts}
    primary_window = usage_core.summarize_usage_window(primary_rows, account_map, "primary")
    secondary_window = usage_core.summarize_usage_window(secondary_rows, account_map, "secondary")
    monthly_window = usage_core.summarize_usage_window(monthly_rows, account_map, "monthly") if monthly_rows else None

    metrics = metrics_override if metrics_override is not None else _usage_metrics(logs_secondary)

    payload = usage_core.parse_usage_summary(primary_window, secondary_window, monthly_window, cost, metrics)
    return _summary_payload_to_response(payload)


def build_usage_history_response(
    *,
    hours: int,
    usage_rows: list[UsageWindowRow],
    accounts: list[Account],
    window: str,
) -> UsageHistoryResponse:
    account_map = {account.id: account for account in accounts}
    accounts_history = _build_account_history(
        usage_rows,
        account_map,
        window,
        missing_remaining_percent=100.0,
    )
    return UsageHistoryResponse(window_hours=hours, accounts=accounts_history)


def build_usage_window_response(
    *,
    window_key: str,
    window_minutes: int | None,
    usage_rows: list[UsageWindowRow],
    accounts: list[Account],
) -> UsageWindowResponse:
    account_map = {account.id: account for account in accounts}
    accounts_history = _build_account_history(
        usage_rows,
        account_map,
        window_key,
        missing_remaining_percent=None,
    )
    return UsageWindowResponse(
        window_key=window_key,
        window_minutes=window_minutes,
        accounts=accounts_history,
    )


def _build_account_history(
    usage_rows: list[UsageWindowRow],
    account_map: dict[str, Account],
    window: str,
    *,
    missing_remaining_percent: float | None,
) -> list[UsageHistoryItem]:
    usage_by_account = {row.account_id: row for row in usage_rows}

    results: list[UsageHistoryItem] = []
    for account_id, account in account_map.items():
        usage = usage_by_account.get(account_id)
        used_percent = usage.used_percent if usage else None
        used_percent_value = float(used_percent) if used_percent is not None else None
        remaining_percent = usage_core.remaining_percent_from_used(used_percent_value)
        if remaining_percent is None:
            remaining_percent = missing_remaining_percent
        capacity = usage_core.capacity_for_plan(account.plan_type, window)
        remaining_credits = usage_core.remaining_credits_from_percent(used_percent_value, capacity)
        if remaining_credits is None and missing_remaining_percent is not None:
            remaining_credits = capacity
        results.append(
            UsageHistoryItem(
                account_id=account_id,
                remaining_percent_avg=remaining_percent,
                capacity_credits=float(capacity or 0.0),
                remaining_credits=float(remaining_credits or 0.0),
            )
        )
    return results


def build_usage_metrics_from_aggregate(aggregate: UsageSummaryLogsAggregate | None) -> UsageMetricsSummary:
    """SQL-aggregate twin of `_usage_metrics`; `None` mirrors an empty window."""
    if aggregate is None or aggregate.request_count == 0:
        requests = aggregate.request_count if aggregate else 0
        return UsageMetricsSummary(
            requests_7d=requests,
            tokens_secondary_window=aggregate.total_tokens if aggregate else 0,
            cached_tokens_secondary_window=aggregate.cached_input_tokens if aggregate else 0,
            error_rate_7d=None,
            top_error=aggregate.top_error if aggregate else None,
            cancelled_7d=aggregate.cancelled_count if aggregate else 0,
        )
    return UsageMetricsSummary(
        requests_7d=aggregate.request_count,
        tokens_secondary_window=aggregate.total_tokens,
        cached_tokens_secondary_window=aggregate.cached_input_tokens,
        error_rate_7d=aggregate.error_count / aggregate.request_count,
        top_error=aggregate.top_error,
        cancelled_7d=aggregate.cancelled_count,
    )


def build_usage_cost_from_aggregate(aggregate: UsageSummaryLogsAggregate | None) -> UsageCostSummary:
    if aggregate is None:
        return UsageCostSummary(currency="USD", total_usd_7d=0.0, by_model=[])
    return UsageCostSummary(
        currency="USD",
        total_usd_7d=round(aggregate.cost_coverage.known_cost_usd, 6),
        by_model=[UsageCostByModel(model=model, usd=round(cost, 6)) for model, cost in sorted(aggregate.cost_by_model)],
        cost_coverage=aggregate.cost_coverage,
    )


def _usage_metrics(logs_secondary: list[RequestLog]) -> UsageMetricsSummary:
    total_requests = len(logs_secondary)
    # Cancelled terminals are normal client disconnects, not upstream
    # failures — they leave the error numerator (and top_error) but stay in
    # the request total (#1552).
    error_logs = [log for log in logs_secondary if log.status not in NON_ERROR_STATUSES]
    cancelled_count = sum(1 for log in logs_secondary if log.status == CANCELLED_STATUS)
    error_rate: float | None = None
    if total_requests > 0:
        error_rate = len(error_logs) / total_requests
    top_error = _top_error_code(error_logs)
    tokens_secondary = _sum_tokens(logs_secondary)
    cached_tokens_secondary = _sum_cached_input_tokens(logs_secondary)
    return UsageMetricsSummary(
        requests_7d=total_requests,
        tokens_secondary_window=tokens_secondary,
        cached_tokens_secondary_window=cached_tokens_secondary,
        error_rate_7d=error_rate,
        top_error=top_error,
        cancelled_7d=cancelled_count,
    )


def _sum_tokens(logs: list[RequestLog]) -> int:
    total = 0
    for log in logs:
        total += total_tokens_from_log(log) or 0
    return total


def _sum_cached_input_tokens(logs: list[RequestLog]) -> int:
    total = 0
    for log in logs:
        total += cached_input_tokens_from_log(log) or 0
    return total


def _top_error_code(logs: list[RequestLog]) -> str | None:
    counts: dict[str, int] = {}
    for log in logs:
        code = log.error_code
        if not code:
            continue
        counts[code] = counts.get(code, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _summary_payload_to_response(payload: UsageSummaryPayload) -> UsageSummaryResponse:
    return UsageSummaryResponse(
        primary_window=build_usage_window_summary_model(payload.primary_window),
        secondary_window=(
            build_usage_window_summary_model(payload.secondary_window) if payload.secondary_window else None
        ),
        monthly_window=(build_usage_window_summary_model(payload.monthly_window) if payload.monthly_window else None),
        cost=_cost_summary_to_model(payload.cost),
        metrics=_metrics_summary_to_model(payload.metrics) if payload.metrics else None,
    )


def build_usage_window_summary_model(snapshot: UsageWindowSnapshot) -> UsageWindow:
    capacity_credits = float(snapshot.capacity_credits)
    remaining_credits = usage_core.remaining_credits_from_used(snapshot.used_credits, capacity_credits) or 0.0
    remaining_percent = max(0.0, 100.0 - float(snapshot.used_percent)) if capacity_credits > 0 else 0.0
    return UsageWindow(
        remaining_percent=remaining_percent,
        capacity_credits=capacity_credits,
        remaining_credits=remaining_credits,
        reset_at=from_epoch_seconds(snapshot.reset_at),
        window_minutes=snapshot.window_minutes,
    )


def _cost_summary_to_model(cost: UsageCostSummary) -> UsageCost:
    return UsageCost(
        currency=cost.currency,
        totalUsd7d=cost.total_usd_7d,
        cost_coverage=cost_coverage_response(cost.cost_coverage),
    )


def _metrics_summary_to_model(metrics: UsageMetricsSummary) -> UsageMetrics:
    return UsageMetrics.model_validate(
        {
            "requests_7d": metrics.requests_7d,
            "tokens_secondary_window": metrics.tokens_secondary_window,
            "cached_tokens_secondary_window": metrics.cached_tokens_secondary_window,
            "error_rate_7d": metrics.error_rate_7d,
            "top_error": metrics.top_error,
            "cancelled_7d": metrics.cancelled_7d,
        }
    )


# ---------------------------------------------------------------------------
# Additional usage aggregation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdditionalWindowSummary:
    """Summary for one window (primary or secondary) of an additional rate limit."""

    used_percent: float  # average across accounts
    reset_at: int | None  # max reset_at across accounts
    window_minutes: int | None  # max window_minutes


@dataclass(frozen=True)
class AdditionalQuotaSummary:
    """Aggregated summary for one additional rate limit (e.g., codex_other)."""

    limit_name: str
    metered_feature: str
    primary_window: AdditionalWindowSummary | None
    secondary_window: AdditionalWindowSummary | None


def build_additional_usage_summary(
    additional_usage_data: dict[str, dict[str, dict[str, AdditionalUsageHistory]]],
) -> list[AdditionalQuotaSummary]:
    """Build aggregated additional quota summaries from per-account data.

    Args:
        additional_usage_data: Nested mapping of
            ``limit_name -> window_key -> account_id -> AdditionalUsageHistory``.

    Returns:
        One :class:`AdditionalQuotaSummary` per *limit_name* present in the input.
    """
    results: list[AdditionalQuotaSummary] = []

    for limit_name, windows in additional_usage_data.items():
        primary_entries = windows.get("primary", {})
        secondary_entries = windows.get("secondary", {})

        # Derive metered_feature from any available entry
        metered_feature = _metered_feature_from_entries(primary_entries, secondary_entries)

        primary_window = _aggregate_additional_window(primary_entries)
        secondary_window = _aggregate_additional_window(secondary_entries)

        results.append(
            AdditionalQuotaSummary(
                limit_name=limit_name,
                metered_feature=metered_feature,
                primary_window=primary_window,
                secondary_window=secondary_window,
            )
        )

    return results


def _aggregate_additional_window(
    entries: dict[str, AdditionalUsageHistory],
) -> AdditionalWindowSummary | None:
    """Aggregate per-account entries into a single window summary.

    Averaging ``used_percent``, using the earliest ``reset_at`` (min) and the
    largest ``window_minutes`` (max) for consistent pool behavior.
    """
    if not entries:
        return None

    total_percent = 0.0
    count = 0
    reset_candidates: list[int] = []
    wm_candidates: list[int] = []

    for entry in entries.values():
        total_percent += entry.used_percent
        count += 1
        if entry.reset_at is not None:
            reset_candidates.append(entry.reset_at)
        if entry.window_minutes is not None:
            wm_candidates.append(entry.window_minutes)

    return AdditionalWindowSummary(
        used_percent=total_percent / count,
        reset_at=min(reset_candidates) if reset_candidates else None,
        window_minutes=max(wm_candidates) if wm_candidates else None,
    )


def _metered_feature_from_entries(
    primary: dict[str, AdditionalUsageHistory],
    secondary: dict[str, AdditionalUsageHistory],
) -> str:
    """Extract ``metered_feature`` from the first available entry."""
    for entries in (primary, secondary):
        for entry in entries.values():
            return entry.metered_feature
    return ""
