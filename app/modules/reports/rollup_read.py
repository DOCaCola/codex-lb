"""Single-snapshot report sources, with exact raw complements of folded buckets."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, case, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from app.db.models import AccountUsageRollupState, RequestLog, RequestReportHourlyRollup
from app.modules.accounts.usage_time_rollup import DIMENSION_SENTINEL, conversation_id_expr, to_dimension
from app.modules.accounts.usage_time_rollup_read import ceil_to_grid, epoch_seconds, floor_to_grid
from app.modules.reports.filters import ReportFilters, _normal_traffic_clause
from app.modules.reports.rollup import MEASURES, raw_measures

DIMENSIONS = ("account_id", "model_source_id", "api_key_id", "model", "useragent_group", "conversation_id")


def _decode(column):
    return case(
        (column == DIMENSION_SENTINEL, None),
        (func.substr(column, 1, 1) == DIMENSION_SENTINEL, func.substr(column, 2)),
        else_=column,
    )


def report_source(
    session: AsyncSession,
    windows: list[tuple[str, datetime, datetime]],
    filters: ReportFilters,
    *,
    catalog: tuple[str, ...] | None = None,
) -> Subquery:
    """UTC hours retain all report filter/distinct dimensions.

    Each day has a folded middle and two possible raw edges. Dynamic tail
    bounds are in the index range condition, so PostgreSQL need not scan all
    historical logs and discard them after checking the watermark.

    A catalog returns only the named dimensions, distinct per raw branch and
    without measures.
    """
    values = [
        select(
            literal(label).label("report_date"),
            literal(start).label("start_at"),
            literal(end).label("end_at"),
            literal(ceil_to_grid(start, 3600)).label("lo_at"),
            literal(floor_to_grid(end, 3600)).label("hi_at"),
            literal(epoch_seconds(ceil_to_grid(start, 3600))).label("lo_epoch"),
            literal(epoch_seconds(floor_to_grid(end, 3600))).label("hi_epoch"),
        )
        for label, start, end in windows
    ]
    w = (values[0] if len(values) == 1 else union_all(*values)).cte("report_windows")
    watermark = func.coalesce(
        select(AccountUsageRollupState.reports_folded_through).where(AccountUsageRollupState.id == 1).scalar_subquery(),
        literal(datetime(1970, 1, 1)),
    )
    watermark_epoch = (
        cast(func.extract("epoch", watermark), BigInteger)
        if session.get_bind().dialect.name == "postgresql"
        else cast(func.strftime("%s", watermark), BigInteger)
    )
    r = RequestReportHourlyRollup
    folded_dimensions = {
        name: r.model if name == "model" else _decode(getattr(r, name)).label(name) for name in DIMENSIONS
    }
    raw_dimensions = {
        **{name: getattr(RequestLog, name) for name in DIMENSIONS[:-1]},
        "conversation_id": conversation_id_expr().label("conversation_id"),
    }
    # Catalog never calculates measures or groups by conversations.
    folded_columns = (
        [folded_dimensions[name] for name in catalog]
        if catalog
        else [w.c.report_date, *folded_dimensions.values(), r.first_requested_at, *(getattr(r, n) for n in MEASURES)]
    )
    folded = (
        select(*folded_columns)
        .select_from(w)
        .join(
            r, (r.bucket_epoch >= w.c.lo_epoch) & (r.bucket_epoch < w.c.hi_epoch) & (r.bucket_epoch < watermark_epoch)
        )
    )
    raw_columns = (
        [raw_dimensions[name] for name in catalog]
        if catalog
        else [
            w.c.report_date,
            *raw_dimensions.values(),
            func.min(RequestLog.requested_at).label("first_requested_at"),
            *raw_measures(),
        ]
    )
    high = case((watermark < w.c.hi_at, watermark), else_=w.c.hi_at)
    tail_start = case((high <= w.c.lo_at, w.c.start_at), else_=high)
    # Filters are applied inside each branch: on stored values for the folded
    # middle, so catalogs can drop the filtered dimensions from their result.
    folded = folded.where(
        *filters.conditions(
            account_id=r.account_id,
            model_source_id=r.model_source_id,
            api_key_id=r.api_key_id,
            model=r.model,
            useragent_group=r.useragent_group,
            encode=to_dimension,
        )
    )
    raw_filters = filters.request_log_conditions()

    def raw(start, end, extra=()):
        stmt = (
            select(*raw_columns)
            .select_from(w)
            .join(RequestLog, (RequestLog.requested_at >= start) & (RequestLog.requested_at < end))
            .where(_normal_traffic_clause(), *raw_filters, *extra)
        )
        return stmt.distinct() if catalog else stmt.group_by(w.c.report_date, *raw_dimensions.values())

    # A leading edge exists only when there is a folded middle.
    branches = [folded, raw(tail_start, w.c.end_at)]
    if any(start != ceil_to_grid(start, 3600) for _, start, _ in windows):
        branches.append(raw(w.c.start_at, w.c.lo_at, (high > w.c.lo_at,)))
    return union_all(*branches).subquery("report_catalog" if catalog else "report_history")
