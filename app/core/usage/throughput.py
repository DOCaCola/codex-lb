"""Provider-specific generation throughput over recorded attempt timings."""

from sqlalchemy import and_, case, func, or_
from sqlalchemy.sql.elements import ColumnElement

from app.core.usage.logs import SUCCESS_STATUS
from app.db.models import RequestLog

GATEWAY_THROUGHPUT_KINDS = ("openrouter", "claude")
MIN_GATEWAY_GENERATION_MS = 1000


def request_tps_expr() -> ColumnElement[float]:
    """Invalid samples are NULL; callers retain their traffic/cohort filters."""
    gateway = RequestLog.model_source_kind.in_(GATEWAY_THROUGHPUT_KINDS)
    tokens = case(
        (gateway, RequestLog.output_tokens),
        else_=RequestLog.output_tokens - func.coalesce(RequestLog.reasoning_tokens, 0),
    )
    elapsed = RequestLog.latency_ms - RequestLog.latency_first_token_ms
    return case(
        (
            and_(
                tokens > 0,
                elapsed > 0,
                or_(
                    RequestLog.model_source_kind.is_(None),
                    ~gateway,
                    and_(
                        RequestLog.status == SUCCESS_STATUS,
                        RequestLog.latency_first_token_ms >= 0,
                        elapsed >= MIN_GATEWAY_GENERATION_MS,
                    ),
                ),
            ),
            tokens * 1000.0 / func.nullif(elapsed, 0),
        )
    )
