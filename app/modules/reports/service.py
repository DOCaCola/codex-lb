from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.utils.time import to_utc_naive, utcnow
from app.modules.reports.filters import ReportFilters
from app.modules.reports.repository import (
    MAX_DAILY_REPORT_DAYS,
    MAX_SPEED_REPORT_DAYS,
    AccountIdentity,
    DailyReportRangeTooLargeError,
    ReportsRepository,
    SplitMeasures,
)
from app.modules.reports.schemas import (
    AccountCostEntry,
    DailyAccountSplit,
    DailyModelSplit,
    DailyReportRow,
    ModelCostEntry,
    ReportAccountOption,
    ReportComparison,
    ReportComparisonPrevious,
    ReportsOptionsResponse,
    ReportsResponse,
    ReportSummary,
    ThreadIdentityFacet,
    ThreadIdentityResponse,
    UserAgentCostEntry,
)
from app.modules.reports.thread_identity import (
    CACHE_MIN_INPUT_TOKENS,
    CONVERSATION_MIN_REQUESTS,
    MAX_THREAD_IDENTITY_DAYS,
    SWITCH_MAX_GAP_SECONDS,
    ThreadIdentityFacetRow,
)


class InvalidReportDateRangeError(ValueError):
    """Raised when a report starts after it ends."""


class ReportsService:
    def __init__(self, repository: ReportsRepository) -> None:
        self._repository = repository

    async def get_reports(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        report_timezone: str | None = None,
        filters: ReportFilters = ReportFilters(),
    ) -> ReportsResponse:
        start_date, end_date, timezone_info = resolve_report_range(start_date, end_date, report_timezone)
        window_days = (end_date - start_date).days + 1

        start_at = _local_midnight_to_utc_naive(start_date, timezone_info)
        end_at = _local_midnight_to_utc_naive(end_date + timedelta(days=1), timezone_info)
        previous_end_date = start_date - timedelta(days=1)
        previous_start_date = previous_end_date - timedelta(days=window_days - 1)
        previous_start_at = _local_midnight_to_utc_naive(previous_start_date, timezone_info)
        previous_end_at = _local_midnight_to_utc_naive(previous_end_date + timedelta(days=1), timezone_info)

        summary = await self._repository.aggregate_summary(start_at, end_at, filters)
        previous_summary = await self._repository.aggregate_summary(previous_start_at, previous_end_at, filters)
        earliest_activity_at = await self._repository.earliest_report_activity_at(filters)
        daily_rows = await self._repository.aggregate_daily_rows(start_date, end_date, timezone_info, filters)
        daily = [
            DailyReportRow(
                date=row.date,
                requests=row.requests,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                reasoning_tokens=row.reasoning_tokens,
                cached_input_tokens=row.cached_input_tokens,
                cost_usd=round(row.cost_usd, 4),
                priced_requests=row.priced_requests,
                unpriced_requests=row.unpriced_requests,
                unmetered_requests=row.unmetered_requests,
                coverage_unknown=row.coverage_unknown,
                active_accounts=row.active_accounts,
                conversations=row.conversation_count,
                error_count=row.error_count,
                cancelled_count=row.cancelled_count,
                median_ttft_ms=round(row.median_ttft_ms, 2),
                median_tps=round(row.median_tps, 2),
                median_queue_ms=round(row.median_queue_ms, 2),
            )
            for row in daily_rows
        ]
        # The daily windows partition the report range, so the per-account and
        # per-model totals are the sums of their daily splits.
        daily_by_account = await self._repository.aggregate_daily_by_account(
            start_date, end_date, timezone_info, filters
        )
        daily_by_model = await self._repository.aggregate_daily_by_model(start_date, end_date, timezone_info, filters)
        by_useragent = await self._repository.aggregate_by_useragent(start_at, end_at, filters)

        account_totals: dict[AccountIdentity, SplitMeasures] = {}
        for row in daily_by_account:
            account_totals[row.account] = _add_measures(account_totals.get(row.account), row.measures)
        model_totals: dict[str, SplitMeasures] = {}
        for row in daily_by_model:
            model_totals[row.model] = _add_measures(model_totals.get(row.model), row.measures)

        comparison = ReportComparison(
            can_compare=earliest_activity_at is not None and earliest_activity_at <= previous_start_at,
            previous=ReportComparisonPrevious(
                total_cost_usd=round(previous_summary.total_cost_usd, 4),
                priced_requests=previous_summary.priced_requests,
                unpriced_requests=previous_summary.unpriced_requests,
                unmetered_requests=previous_summary.unmetered_requests,
                coverage_unknown=previous_summary.coverage_unknown,
                total_tokens=previous_summary.total_input_tokens + previous_summary.total_output_tokens,
                total_requests=previous_summary.total_requests,
            ),
        )

        return ReportsResponse(
            speed_metrics_available=window_days <= MAX_SPEED_REPORT_DAYS,
            speed_metrics_max_days=MAX_SPEED_REPORT_DAYS,
            summary=ReportSummary(
                total_cost_usd=round(summary.total_cost_usd, 4),
                priced_requests=summary.priced_requests,
                unpriced_requests=summary.unpriced_requests,
                unmetered_requests=summary.unmetered_requests,
                coverage_unknown=summary.coverage_unknown,
                total_input_tokens=summary.total_input_tokens,
                total_output_tokens=summary.total_output_tokens,
                total_reasoning_tokens=summary.total_reasoning_tokens,
                reasoning_usage_known_requests=summary.reasoning_usage_known_requests,
                total_cached_tokens=summary.total_cached_tokens,
                total_requests=summary.total_requests,
                total_errors=summary.total_errors,
                total_cancelled=summary.total_cancelled,
                active_accounts=summary.active_accounts,
                total_conversations=summary.conversation_count,
                avg_cost_per_day=round(summary.total_cost_usd / window_days, 4),
                avg_requests_per_day=round(summary.total_requests / window_days, 2),
            ),
            comparison=comparison,
            daily=daily,
            daily_by_account=[
                DailyAccountSplit(
                    date=row.date,
                    account_id=row.account.account_id,
                    model_source_id=row.account.model_source_id,
                    provider=row.account.provider,
                    name=row.account.name,
                    **_split_fields(row.measures),
                )
                for row in daily_by_account
            ],
            daily_by_model=[
                DailyModelSplit(date=row.date, model=row.model, **_split_fields(row.measures)) for row in daily_by_model
            ],
            by_model=[
                ModelCostEntry(
                    model=model,
                    cost_usd=round(total.cost_usd, 4),
                    requests=total.requests,
                    priced_requests=total.priced_requests,
                    unpriced_requests=total.unpriced_requests,
                    unmetered_requests=total.unmetered_requests,
                    coverage_unknown=total.coverage_unknown,
                )
                for model, total in sorted(model_totals.items(), key=lambda item: (-item[1].cost_usd, item[0]))
            ],
            by_account=[
                AccountCostEntry(
                    account_id=account.account_id,
                    model_source_id=account.model_source_id,
                    provider=account.provider,
                    name=account.name,
                    cost_usd=round(total.cost_usd, 4),
                    requests=total.requests,
                    priced_requests=total.priced_requests,
                    unpriced_requests=total.unpriced_requests,
                    unmetered_requests=total.unmetered_requests,
                    coverage_unknown=total.coverage_unknown,
                )
                for account, total in sorted(
                    account_totals.items(),
                    key=lambda item: (-item[1].cost_usd, item[0].account_id or "", item[0].model_source_id or ""),
                )
            ],
            by_useragent=[
                UserAgentCostEntry(
                    useragent=u.useragent_group,
                    cost_usd=round(u.cost_usd, 4),
                    requests=u.request_count,
                    priced_requests=u.priced_requests,
                    unpriced_requests=u.unpriced_requests,
                    unmetered_requests=u.unmetered_requests,
                    coverage_unknown=u.coverage_unknown,
                )
                for u in by_useragent
            ],
        )

    async def get_thread_identity(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        report_timezone: str | None = None,
    ) -> ThreadIdentityResponse:
        start_date, end_date, timezone_info = resolve_report_range(start_date, end_date, report_timezone)
        window_days = (end_date - start_date).days + 1
        # Mirrors the speed medians: a range too wide to scan raw request logs
        # answers "unavailable" instead of costing the database the scan.
        available = window_days <= MAX_THREAD_IDENTITY_DAYS
        total_requests = 0
        keyed = unkeyed = ThreadIdentityFacet()
        unkeyed_request_share = 0.0
        if available:
            facets = await self._repository.aggregate_thread_identity(
                _local_midnight_to_utc_naive(start_date, timezone_info),
                _local_midnight_to_utc_naive(end_date + timedelta(days=1), timezone_info),
            )
            keyed_row, unkeyed_row = facets[True], facets[False]
            total_requests = keyed_row.requests + unkeyed_row.requests
            unkeyed_request_share = _ratio(unkeyed_row.requests, total_requests)
            keyed = _thread_identity_facet(keyed_row, total_requests, approximate=False)
            unkeyed = _thread_identity_facet(unkeyed_row, total_requests, approximate=True)
        return ThreadIdentityResponse(
            available=available,
            max_days=MAX_THREAD_IDENTITY_DAYS,
            window_days=window_days,
            conversation_min_requests=CONVERSATION_MIN_REQUESTS,
            switch_max_gap_seconds=SWITCH_MAX_GAP_SECONDS,
            cache_min_input_tokens=CACHE_MIN_INPUT_TOKENS,
            total_requests=total_requests,
            unkeyed_request_share=unkeyed_request_share,
            keyed=keyed,
            unkeyed=unkeyed,
        )

    async def get_options(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        report_timezone: str | None = None,
        filters: ReportFilters = ReportFilters(),
    ) -> ReportsOptionsResponse:
        start_date, end_date, timezone_info = resolve_report_range(start_date, end_date, report_timezone)
        start_at = _local_midnight_to_utc_naive(start_date, timezone_info)
        end_at = _local_midnight_to_utc_naive(end_date + timedelta(days=1), timezone_info)
        models, useragents = await self._repository.list_filter_options(start_at, end_at, filters)
        accounts = await self._repository.list_account_options(start_at, end_at, filters)
        return ReportsOptionsResponse(
            models=models,
            useragents=useragents,
            accounts=[
                ReportAccountOption(
                    account_id=account.account_id,
                    model_source_id=account.model_source_id,
                    provider=account.provider,
                    name=account.name,
                )
                for account in accounts
            ],
        )


def resolve_report_range(
    start_date: date | None,
    end_date: date | None,
    report_timezone: str | None,
) -> tuple[date, date, ZoneInfo | timezone]:
    timezone_info = _resolve_timezone(report_timezone)
    end_date = end_date or utcnow().replace(tzinfo=timezone.utc).astimezone(timezone_info).date()
    start_date = start_date or end_date - timedelta(days=6)
    if start_date > end_date:
        raise InvalidReportDateRangeError("start_date must be on or before end_date")
    if (end_date - start_date).days + 1 > MAX_DAILY_REPORT_DAYS:
        raise DailyReportRangeTooLargeError(f"report date range must be {MAX_DAILY_REPORT_DAYS} days or less")
    return start_date, end_date, timezone_info


def _resolve_timezone(timezone_name: str | None) -> ZoneInfo | timezone:
    if not timezone_name:
        return timezone.utc
    try:
        return ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError):
        return timezone.utc


def _local_midnight_to_utc_naive(value: date, timezone_info: ZoneInfo | timezone) -> datetime:
    return to_utc_naive(datetime.combine(value, datetime.min.time(), tzinfo=timezone_info))


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator > 0 else 0.0


def _thread_identity_facet(
    row: ThreadIdentityFacetRow,
    total_requests: int,
    *,
    approximate: bool,
) -> ThreadIdentityFacet:
    return ThreadIdentityFacet(
        requests=row.requests,
        request_share=_ratio(row.requests, total_requests),
        unattributed_request_share=_ratio(row.unattributed_requests, row.requests),
        conversations=row.conversations,
        mean_accounts_per_conversation=round(row.conversation_account_total / row.conversations, 4)
        if row.conversations > 0
        else 0.0,
        single_account_conversation_share=_ratio(row.single_account_conversations, row.conversations),
        turns=row.turns,
        account_switch_rate=_ratio(row.account_switches, row.turns),
        cache_hit_ratio=_ratio(row.cache_cached_input_tokens, row.cache_input_tokens),
        cache_sample_input_tokens=row.cache_input_tokens,
        thread_grouping_approximate=approximate,
    )


def _add_measures(total: SplitMeasures | None, value: SplitMeasures) -> SplitMeasures:
    if total is None:
        return value
    reasoning = (
        None
        if total.reasoning_tokens is None and value.reasoning_tokens is None
        else (total.reasoning_tokens or 0) + (value.reasoning_tokens or 0)
    )
    return SplitMeasures(
        requests=total.requests + value.requests,
        input_tokens=total.input_tokens + value.input_tokens,
        cached_input_tokens=total.cached_input_tokens + value.cached_input_tokens,
        output_tokens=total.output_tokens + value.output_tokens,
        reasoning_tokens=reasoning,
        cost_usd=total.cost_usd + value.cost_usd,
        priced_requests=total.priced_requests + value.priced_requests,
        unpriced_requests=total.unpriced_requests + value.unpriced_requests,
        unmetered_requests=total.unmetered_requests + value.unmetered_requests,
        coverage_unknown=total.coverage_unknown or value.coverage_unknown,
    )


def _split_fields(measures: SplitMeasures) -> dict:
    return {
        "requests": measures.requests,
        "input_tokens": measures.input_tokens,
        "cached_input_tokens": measures.cached_input_tokens,
        "output_tokens": measures.output_tokens,
        "reasoning_tokens": measures.reasoning_tokens,
        "cost_usd": round(measures.cost_usd, 4),
        "priced_requests": measures.priced_requests,
        "unpriced_requests": measures.unpriced_requests,
        "unmetered_requests": measures.unmetered_requests,
        "coverage_unknown": measures.coverage_unknown,
    }
