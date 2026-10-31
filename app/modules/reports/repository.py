from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from itertools import batched
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage.throughput import request_tps_expr
from app.db.models import Account, ModelSource, RequestLog
from app.modules.accounts.provider_accounts import (
    AccountProvider,
    provider_account_key,
    provider_account_name_expr,
    provider_account_provider_expr,
)
from app.modules.reports.filters import (
    MISSING_USERAGENT_GROUP,
    ReportFilters,
    _normal_traffic_clause,
)
from app.modules.reports.rollup import MEASURES
from app.modules.reports.rollup_read import report_source
from app.modules.reports.thread_identity import ThreadIdentityFacetRow, aggregate_thread_identity

_SQLITE_COMPOUND_SELECT_LIMIT = 500
MAX_DAILY_REPORT_DAYS = 730
MAX_SPEED_REPORT_DAYS = 7
_NO_FILTERS = ReportFilters()
_COVERAGE = ("priced_requests", "unpriced_requests", "unmetered_requests", "coverage_unknown")


class DailyReportRangeTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class DailyReportAggregateRow:
    date: str
    requests: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None
    cached_input_tokens: int
    cost_usd: float
    active_accounts: int
    error_count: int
    median_ttft_ms: float
    median_tps: float
    median_queue_ms: float
    conversation_count: int = 0
    cancelled_count: int = 0
    priced_requests: int = 0
    unpriced_requests: int = 0
    unmetered_requests: int = 0
    coverage_unknown: bool = False


@dataclass(frozen=True)
class SummaryAggregateRow:
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_reasoning_tokens: int
    reasoning_usage_known_requests: int
    total_cached_tokens: int
    total_requests: int
    total_errors: int
    active_accounts: int
    conversation_count: int = 0
    total_cancelled: int = 0
    priced_requests: int = 0
    unpriced_requests: int = 0
    unmetered_requests: int = 0
    coverage_unknown: bool = False


@dataclass(frozen=True)
class SplitMeasures:
    """One day's usage of one account or model."""

    requests: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None
    cost_usd: float
    error_count: int
    priced_requests: int = 0
    unpriced_requests: int = 0
    unmetered_requests: int = 0
    coverage_unknown: bool = False


@dataclass(frozen=True)
class AccountIdentity:
    account_id: str | None
    model_source_id: str | None
    provider: AccountProvider | None
    name: str | None


@dataclass(frozen=True)
class DailyAccountAggregateRow:
    date: str
    account: AccountIdentity
    measures: SplitMeasures


@dataclass(frozen=True)
class DailyModelAggregateRow:
    date: str
    model: str
    measures: SplitMeasures


@dataclass(frozen=True)
class UserAgentAggregateRow:
    useragent_group: str
    cost_usd: float
    request_count: int
    priced_requests: int = 0
    unpriced_requests: int = 0
    unmetered_requests: int = 0
    coverage_unknown: bool = False


class ReportsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def aggregate_daily_rows(
        self,
        start_date: date,
        end_date: date,
        timezone_info: ZoneInfo | timezone,
        filters: ReportFilters = _NO_FILTERS,
    ) -> list[DailyReportAggregateRow]:
        speed_available = (end_date - start_date).days + 1 <= MAX_SPEED_REPORT_DAYS
        rows: list[DailyReportAggregateRow] = []
        for windows in _daily_window_batches(start_date, end_date, timezone_info):
            speed_values: dict[str, tuple[float, float, float]] = {}
            if speed_available:
                speeds = await self._session.execute(_daily_speed_medians_stmt(windows, filters))
                speed_values = {
                    row.report_date: (
                        float(row.median_ttft_ms or 0),
                        float(row.median_tps or 0),
                        float(row.median_queue_ms or 0),
                    )
                    for row in speeds
                }
            source = report_source(self._session, windows, filters)
            result = await self._session.execute(
                select(source.c.report_date, *_aggregate_columns(source))
                .group_by(source.c.report_date)
                .order_by(source.c.report_date)
            )
            for row in result:
                speed = speed_values.get(row.report_date, (0.0, 0.0, 0.0))
                rows.append(
                    DailyReportAggregateRow(
                        date=row.report_date,
                        requests=int(row.request_count),
                        input_tokens=int(row.input_tokens),
                        output_tokens=int(row.output_tokens),
                        reasoning_tokens=int(row.reasoning_tokens) if row.reasoning_usage_known_requests else None,
                        cached_input_tokens=int(row.cached_input_tokens),
                        cost_usd=float(row.cost_usd),
                        priced_requests=int(row.priced_requests),
                        unpriced_requests=int(row.unpriced_requests),
                        unmetered_requests=int(row.unmetered_requests),
                        coverage_unknown=bool(row.coverage_unknown),
                        active_accounts=int(row.active_accounts),
                        error_count=int(row.error_count),
                        cancelled_count=int(row.cancelled_count),
                        conversation_count=int(row.conversation_count),
                        median_ttft_ms=speed[0],
                        median_tps=speed[1],
                        median_queue_ms=speed[2],
                    )
                )
        return rows

    async def aggregate_daily_by_account(
        self,
        start_date: date,
        end_date: date,
        timezone_info: ZoneInfo | timezone,
        filters: ReportFilters = _NO_FILTERS,
    ) -> list[DailyAccountAggregateRow]:
        rows: list[DailyAccountAggregateRow] = []
        for windows in _daily_window_batches(start_date, end_date, timezone_info):
            source = report_source(self._session, windows, filters)
            result = await self._session.execute(
                _with_account_identity(
                    select(source.c.report_date, *_account_identity_columns(source), *_split_measure_columns(source)),
                    source,
                )
                .group_by(source.c.report_date, *_account_identity_group(source))
                .order_by(source.c.report_date, source.c.account_id, source.c.model_source_id)
            )
            rows.extend(
                DailyAccountAggregateRow(row.report_date, _account_identity(row), _split_measures(row))
                for row in result
            )
        return rows

    async def aggregate_daily_by_model(
        self,
        start_date: date,
        end_date: date,
        timezone_info: ZoneInfo | timezone,
        filters: ReportFilters = _NO_FILTERS,
    ) -> list[DailyModelAggregateRow]:
        rows: list[DailyModelAggregateRow] = []
        for windows in _daily_window_batches(start_date, end_date, timezone_info):
            source = report_source(self._session, windows, filters)
            result = await self._session.execute(
                select(source.c.report_date, source.c.model, *_split_measure_columns(source))
                .group_by(source.c.report_date, source.c.model)
                .order_by(source.c.report_date, source.c.model)
            )
            rows.extend(DailyModelAggregateRow(row.report_date, row.model, _split_measures(row)) for row in result)
        return rows

    async def aggregate_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: ReportFilters = _NO_FILTERS,
    ) -> SummaryAggregateRow:
        source = report_source(self._session, [("summary", start_date, end_date)], filters)
        row = (await self._session.execute(select(*_aggregate_columns(source)))).one()
        return SummaryAggregateRow(
            total_cost_usd=float(row.cost_usd),
            priced_requests=int(row.priced_requests),
            unpriced_requests=int(row.unpriced_requests),
            unmetered_requests=int(row.unmetered_requests),
            coverage_unknown=bool(row.coverage_unknown),
            total_input_tokens=int(row.input_tokens),
            total_output_tokens=int(row.output_tokens),
            total_reasoning_tokens=int(row.reasoning_tokens),
            reasoning_usage_known_requests=int(row.reasoning_usage_known_requests),
            total_cached_tokens=int(row.cached_input_tokens),
            total_requests=int(row.request_count),
            total_errors=int(row.error_count),
            total_cancelled=int(row.cancelled_count),
            active_accounts=int(row.active_accounts),
            conversation_count=int(row.conversation_count),
        )

    async def aggregate_by_useragent(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: ReportFilters = _NO_FILTERS,
    ) -> list[UserAgentAggregateRow]:
        source = report_source(self._session, [("useragents", start_date, end_date)], filters)
        group = func.coalesce(source.c.useragent_group, MISSING_USERAGENT_GROUP)
        result = await self._session.execute(
            select(
                group.label("useragent_group"),
                func.sum(source.c.cost_usd).label("cost_usd"),
                func.sum(source.c.request_count).label("request_count"),
                *(func.sum(getattr(source.c, name)).label(name) for name in _COVERAGE),
            )
            .where(or_(source.c.useragent_group.is_(None), func.trim(source.c.useragent_group) != ""))
            .group_by(group)
            .order_by(func.sum(source.c.cost_usd).desc(), group)
        )
        return [
            UserAgentAggregateRow(
                row.useragent_group,
                float(row.cost_usd),
                int(row.request_count),
                int(row.priced_requests),
                int(row.unpriced_requests),
                int(row.unmetered_requests),
                bool(row.coverage_unknown),
            )
            for row in result
        ]

    async def aggregate_thread_identity(
        self,
        start_at: datetime,
        end_at: datetime,
    ) -> dict[bool, ThreadIdentityFacetRow]:
        """Keyed and unkeyed thread-identity counters for one bounded window.

        Deliberately unfiltered by account, API key, model or user agent: an
        account filter would force every conversation to one account and make
        the accounts-per-conversation factor read 1.0 by construction.
        """
        return await aggregate_thread_identity(self._session, start_at, end_at)

    async def earliest_report_activity_at(self, filters: ReportFilters = _NO_FILTERS) -> datetime | None:
        source = report_source(
            self._session,
            [("earliest", datetime(1970, 1, 1), datetime(9998, 1, 1))],
            filters,
        )
        return (await self._session.execute(select(func.min(source.c.first_requested_at)))).scalar_one_or_none()

    async def list_filter_options(
        self,
        start_at: datetime,
        end_at: datetime,
        filters: ReportFilters = _NO_FILTERS,
    ) -> tuple[list[str], list[str]]:
        """Models and user agents within the account and API-key scope."""
        source = report_source(
            self._session,
            [("options", start_at, end_at)],
            filters.without_selection(),
            catalog=("model", "useragent_group"),
        )
        pairs = (await self._session.execute(select(source.c.model, source.c.useragent_group).distinct())).all()
        return sorted({row.model for row in pairs}), sorted(
            {
                row.useragent_group if row.useragent_group is not None else MISSING_USERAGENT_GROUP
                for row in pairs
                if row.useragent_group is None or row.useragent_group.strip()
            }
        )

    async def list_account_options(
        self,
        start_at: datetime,
        end_at: datetime,
        filters: ReportFilters = _NO_FILTERS,
    ) -> list[AccountIdentity]:
        """Accounts with usage within the API-key scope; the account selection does not narrow them."""
        source = report_source(
            self._session,
            [("account_options", start_at, end_at)],
            filters.api_keys_only(),
            catalog=("account_id", "model_source_id"),
        )
        pairs = select(source.c.account_id, source.c.model_source_id).distinct().subquery("account_pairs")
        result = await self._session.execute(
            _with_account_identity(select(*_account_identity_columns(pairs)), pairs).where(
                or_(pairs.c.account_id.is_not(None), pairs.c.model_source_id.is_not(None))
            )
        )
        identities = [_account_identity(row) for row in result]
        return sorted(identities, key=lambda identity: ((identity.name or "").casefold(), _identity_key(identity)))


def _identity_key(identity: AccountIdentity) -> str:
    return f"source:{identity.model_source_id}" if identity.model_source_id else f"account:{identity.account_id}"


def _daily_window_batches(
    start_date: date,
    end_date: date,
    timezone_info: ZoneInfo | timezone,
) -> Iterator[list[tuple[str, datetime, datetime]]]:
    if (end_date - start_date).days + 1 > MAX_DAILY_REPORT_DAYS:
        raise DailyReportRangeTooLargeError(f"report date range must be {MAX_DAILY_REPORT_DAYS} days or less")
    for batch in batched(_daily_bucket_ranges(start_date, end_date, timezone_info), _SQLITE_COMPOUND_SELECT_LIMIT):
        yield list(batch)


def _aggregate_columns(source) -> list:
    return [
        *(func.coalesce(func.sum(getattr(source.c, name)), 0).label(name) for name in MEASURES),
        func.count(func.distinct(provider_account_key(source.c.account_id, source.c.model_source_id))).label(
            "active_accounts"
        ),
        func.count(func.distinct(source.c.conversation_id)).label("conversation_count"),
    ]


_SPLIT_SUMS = (
    "request_count",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "reasoning_usage_known_requests",
    "cost_usd",
    "error_count",
    *_COVERAGE,
)


def _split_measure_columns(source) -> list:
    return [func.coalesce(func.sum(getattr(source.c, name)), 0).label(name) for name in _SPLIT_SUMS]


def _split_measures(row) -> SplitMeasures:
    return SplitMeasures(
        requests=int(row.request_count),
        input_tokens=int(row.input_tokens),
        cached_input_tokens=int(row.cached_input_tokens),
        output_tokens=int(row.output_tokens),
        reasoning_tokens=int(row.reasoning_tokens) if row.reasoning_usage_known_requests else None,
        cost_usd=float(row.cost_usd),
        error_count=int(row.error_count),
        priced_requests=int(row.priced_requests),
        unpriced_requests=int(row.unpriced_requests),
        unmetered_requests=int(row.unmetered_requests),
        coverage_unknown=bool(row.coverage_unknown),
    )


def _with_account_identity(stmt, source):
    return stmt.outerjoin(Account, Account.id == source.c.account_id).outerjoin(
        ModelSource, ModelSource.id == source.c.model_source_id
    )


def _account_identity_columns(source) -> list:
    return [
        source.c.account_id,
        source.c.model_source_id,
        provider_account_provider_expr().label("provider"),
        provider_account_name_expr().label("name"),
    ]


def _account_identity_group(source) -> tuple:
    return (
        source.c.account_id,
        source.c.model_source_id,
        Account.id,
        Account.alias,
        Account.email,
        ModelSource.id,
        ModelSource.name,
        ModelSource.kind,
    )


def _account_identity(row) -> AccountIdentity:
    return AccountIdentity(row.account_id, row.model_source_id, row.provider, row.name)


def _day_ranges_cte(day_ranges: list[tuple[str, datetime, datetime]]):
    day_range_rows = [
        select(
            literal(report_date).label("report_date"),
            literal(day_start).label("day_start"),
            literal(day_end).label("day_end"),
        )
        for report_date, day_start, day_end in day_ranges
    ]
    day_ranges_query = day_range_rows[0] if len(day_range_rows) == 1 else union_all(*day_range_rows)
    return day_ranges_query.cte("report_days")


def _daily_speed_medians_stmt(
    day_ranges: list[tuple[str, datetime, datetime]],
    filters: ReportFilters,
):
    day_ranges_cte = _day_ranges_cte(day_ranges)
    # Constant outer bounds let PostgreSQL range-scan the requested_at index;
    # the per-day join below only assigns each sampled row to its report day.
    range_start = day_ranges[0][1]
    range_end = day_ranges[-1][2]
    # One samples CTE serves all three metrics. Because it is referenced more
    # than once, PostgreSQL materializes it and reads request_logs a single time.
    samples_cte = (
        select(
            day_ranges_cte.c.report_date,
            RequestLog.latency_first_token_ms.label("ttft_ms"),
            request_tps_expr().label("tps"),
            RequestLog.latency_queue_ms.label("queue_ms"),
        )
        .select_from(
            day_ranges_cte.join(
                RequestLog,
                and_(
                    RequestLog.requested_at >= day_ranges_cte.c.day_start,
                    RequestLog.requested_at < day_ranges_cte.c.day_end,
                ),
            )
        )
        .where(
            RequestLog.requested_at >= range_start,
            RequestLog.requested_at < range_end,
            _normal_traffic_clause(),
            *filters.request_log_conditions(),
        )
        .cte("daily_speed_samples")
    )
    ttft_medians_cte = _daily_median_cte(samples_cte, "ttft_ms", "median_ttft_ms")
    tps_medians_cte = _daily_median_cte(samples_cte, "tps", "median_tps")
    queue_medians_cte = _daily_median_cte(samples_cte, "queue_ms", "median_queue_ms")
    return (
        select(
            day_ranges_cte.c.report_date,
            func.coalesce(ttft_medians_cte.c.median_ttft_ms, 0.0).label("median_ttft_ms"),
            func.coalesce(tps_medians_cte.c.median_tps, 0.0).label("median_tps"),
            func.coalesce(queue_medians_cte.c.median_queue_ms, 0.0).label("median_queue_ms"),
        )
        .select_from(
            day_ranges_cte.outerjoin(
                ttft_medians_cte,
                ttft_medians_cte.c.report_date == day_ranges_cte.c.report_date,
            )
            .outerjoin(
                tps_medians_cte,
                tps_medians_cte.c.report_date == day_ranges_cte.c.report_date,
            )
            .outerjoin(
                queue_medians_cte,
                queue_medians_cte.c.report_date == day_ranges_cte.c.report_date,
            )
        )
        .order_by(day_ranges_cte.c.report_date)
    )


def _daily_median_cte(samples_cte, metric: str, label: str):
    value = samples_cte.c[metric]
    ranked_cte = (
        select(
            samples_cte.c.report_date,
            value.label("value"),
            func.count().over(partition_by=samples_cte.c.report_date).label("sample_count"),
            func.row_number().over(partition_by=samples_cte.c.report_date, order_by=value).label("value_rank"),
        )
        .where(value.is_not(None))
        .cte(f"daily_{metric}_ranks")
    )
    # A median contains the one center row for odd samples and both center rows
    # for even samples. Multiplication avoids dialect-specific integer division.
    is_middle = and_(
        ranked_cte.c.value_rank * 2 >= ranked_cte.c.sample_count,
        ranked_cte.c.value_rank * 2 <= ranked_cte.c.sample_count + 2,
    )
    return (
        select(
            ranked_cte.c.report_date,
            func.avg(case((is_middle, ranked_cte.c.value), else_=None)).label(label),
        )
        .group_by(ranked_cte.c.report_date)
        .cte(f"daily_{metric}_medians")
    )


def _daily_bucket_ranges(
    start_date: date,
    end_date: date,
    timezone_info: ZoneInfo | timezone,
) -> list[tuple[str, datetime, datetime]]:
    ranges: list[tuple[str, datetime, datetime]] = []
    current_date = start_date
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone_info)
        next_day_start = datetime.combine(current_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone_info)
        ranges.append(
            (
                current_date.isoformat(),
                day_start.astimezone(timezone.utc).replace(tzinfo=None),
                next_day_start.astimezone(timezone.utc).replace(tzinfo=None),
            )
        )
        current_date += timedelta(days=1)
    return ranges
