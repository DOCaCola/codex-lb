"""Bounded SQL observations over existing logs; no payload or transcript reads."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.usage.logs import CANCELLED_STATUS, NON_ERROR_STATUSES, SUCCESS_STATUS
from app.core.usage.throughput import request_tps_expr
from app.db.models import RequestLog
from app.modules.accounts.provider_accounts import provider_account_key
from app.modules.accounts.usage_time_rollup import _requested_at_epoch_bucket_expr
from app.modules.reports.filters import _normal_traffic_clause

GENERATION_OPERATIONS = ("responses", "messages", "chat_completions", "unknown")


def generation_clause() -> ColumnElement[bool]:
    return or_(RequestLog.request_operation.is_(None), RequestLog.request_operation.in_(GENERATION_OPERATIONS))


def provider_account_expr() -> ColumnElement[str | None]:
    return provider_account_key(RequestLog.account_id, RequestLog.model_source_id)


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
