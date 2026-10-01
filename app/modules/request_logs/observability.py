"""Bounded SQL observations over existing logs; no payload or transcript reads."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.usage.logs import CANCELLED_STATUS, NON_ERROR_STATUSES, SUCCESS_STATUS
from app.core.usage.throughput import request_tps_expr
from app.db.models import RequestLog
from app.modules.accounts.usage_time_rollup import _requested_at_epoch_bucket_expr
from app.modules.reports.filters import _normal_traffic_clause

GENERATION_OPERATIONS = ("responses", "messages", "chat_completions", "unknown")


def generation_clause() -> ColumnElement[bool]:
    return or_(RequestLog.request_operation.is_(None), RequestLog.request_operation.in_(GENERATION_OPERATIONS))


def provider_account_expr() -> ColumnElement[str]:
    # Source and subscription identifiers occupy different namespaces.
    return func.coalesce(literal("source:") + RequestLog.model_source_id, literal("account:") + RequestLog.account_id)


@dataclass(frozen=True)
class CacheWindowRow:
    requests: int = 0
    measured_requests: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class CacheActivityRow:
    source_id: str | None
    model: str
    current: CacheWindowRow
    previous: CacheWindowRow


async def read_cache_activity(session: AsyncSession, now: datetime) -> list[CacheActivityRow]:
    current_start = now - timedelta(hours=1)
    previous_start = now - timedelta(hours=2)
    measured = and_(
        RequestLog.input_tokens.is_not(None),
        RequestLog.cached_input_tokens.is_not(None),
        RequestLog.cache_creation_tokens.is_not(None),
        RequestLog.input_tokens >= 0,
        RequestLog.cached_input_tokens >= 0,
        RequestLog.cache_creation_tokens >= 0,
        RequestLog.cached_input_tokens + RequestLog.cache_creation_tokens <= RequestLog.input_tokens,
    )
    period = case((RequestLog.requested_at >= current_start, "current"), else_="previous")
    rows = (
        await session.execute(
            select(
                RequestLog.model_source_id.label("source_id"),
                RequestLog.model,
                period.label("period"),
                func.count().label("requests"),
                func.sum(case((measured, 1), else_=0)).label("measured_requests"),
                func.sum(case((measured, RequestLog.input_tokens), else_=0)).label("input_tokens"),
                func.sum(case((measured, RequestLog.cached_input_tokens), else_=0)).label("cache_read_tokens"),
                func.sum(case((measured, RequestLog.cache_creation_tokens), else_=0)).label("cache_write_tokens"),
            )
            .where(
                RequestLog.requested_at >= previous_start,
                RequestLog.requested_at < now,
                RequestLog.model_source_kind == "claude",
                RequestLog.status == SUCCESS_STATUS,
                RequestLog.deleted_at.is_(None),
                _normal_traffic_clause(),
                generation_clause(),
            )
            .group_by(RequestLog.model_source_id, RequestLog.model, period)
        )
    ).all()
    groups: dict[tuple[str | None, str], dict[str, CacheWindowRow]] = {}
    for row in rows:
        groups.setdefault((row.source_id, row.model), {})[row.period] = CacheWindowRow(
            requests=row.requests,
            measured_requests=row.measured_requests,
            input_tokens=row.input_tokens,
            cache_read_tokens=row.cache_read_tokens,
            cache_write_tokens=row.cache_write_tokens,
        )
    return [
        CacheActivityRow(
            source_id, model, windows.get("current", CacheWindowRow()), windows.get("previous", CacheWindowRow())
        )
        for (source_id, model), windows in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0] or ""))
    ]


@dataclass(frozen=True)
class ConversationPerformanceRow:
    model: str
    reasoning_effort: str | None
    requests: int
    errors: int
    cancelled: int
    mean_ttft_ms: float | None
    ttft_samples: int
    mean_tps: float | None
    tps_samples: int
    cache_write_tokens: int
    cache_write_samples: int


@dataclass(frozen=True)
class ConversationActivityRow:
    bucket_epoch: int
    requests: int
    errors: int
    cancelled: int


@dataclass(frozen=True)
class ConversationAnalyticsRows:
    start: datetime
    end: datetime
    models: list[ConversationPerformanceRow]
    activity: list[ConversationActivityRow]


async def read_conversation_analytics(
    session: AsyncSession,
    conversation_id: str,
    latest: datetime,
) -> ConversationAnalyticsRows:
    # JavaScript dates retain milliseconds, so the exclusive endpoint must
    # remain later than the last request after dashboard serialization.
    end = latest + timedelta(milliseconds=1)
    start = end - timedelta(days=7)
    conditions = [
        RequestLog.conversation_id == conversation_id,
        RequestLog.requested_at >= start,
        RequestLog.requested_at < end,
        RequestLog.deleted_at.is_(None),
        _normal_traffic_clause(),
    ]
    success = and_(RequestLog.status == SUCCESS_STATUS, generation_clause())
    ttft = case((and_(success, RequestLog.latency_first_token_ms >= 0), RequestLog.latency_first_token_ms))
    tps = case(
        (
            and_(success, RequestLog.latency_first_token_ms >= 0),
            request_tps_expr(),
        )
    )
    errors = case((RequestLog.status.not_in(NON_ERROR_STATUSES), 1), else_=0)
    cancelled = case((RequestLog.status == CANCELLED_STATUS, 1), else_=0)
    rows = (
        await session.execute(
            select(
                RequestLog.model,
                RequestLog.reasoning_effort,
                func.count().label("requests"),
                func.sum(errors).label("errors"),
                func.sum(cancelled).label("cancelled"),
                func.avg(ttft).label("mean_ttft_ms"),
                func.count(ttft).label("ttft_samples"),
                func.avg(tps).label("mean_tps"),
                func.count(tps).label("tps_samples"),
                func.coalesce(func.sum(RequestLog.cache_creation_tokens), 0).label("cache_write_tokens"),
                func.count(RequestLog.cache_creation_tokens).label("cache_write_samples"),
            )
            .where(*conditions)
            .group_by(RequestLog.model, RequestLog.reasoning_effort)
            .order_by(RequestLog.model, RequestLog.reasoning_effort)
        )
    ).all()
    bucket = _requested_at_epoch_bucket_expr(session, 3600)
    series = (
        await session.execute(
            select(
                bucket.label("bucket_epoch"),
                func.count().label("requests"),
                func.sum(errors).label("errors"),
                func.sum(cancelled).label("cancelled"),
            )
            .where(*conditions)
            .group_by(bucket)
            .order_by(bucket)
        )
    ).all()
    return ConversationAnalyticsRows(
        start,
        end,
        [ConversationPerformanceRow(**row._mapping) for row in rows],
        [ConversationActivityRow(**row._mapping) for row in series],
    )
