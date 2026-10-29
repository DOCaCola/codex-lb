"""Bounded proxy-side recovery for Antigravity inference (design section 9).

The Codex and Claude Code clients run their own retry loops, so recovery here is
small and explicit: it never replays after output reached the client, never walks
the pool for request defects, and spends at most MAX_SENDS upstream sends.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import cast

from app.core.types import JsonValue
from app.db.session import get_background_session
from app.modules.antigravity.classify import UpstreamFailure
from app.modules.antigravity.failures import MOVE_THRESHOLD, record_failure
from app.modules.antigravity.repository import AntigravityRepository
from app.modules.antigravity.schemas import QuotaFamily
from app.modules.model_sources.forwarding import ModelSourceForwardingError, _redact_json_value

logger = logging.getLogger(__name__)

MAX_SENDS = 4
# Upstream 429 answers one request may absorb before reporting (OmniRoute #18140).
MAX_UPSTREAM_429 = 2


def _error(kind: str, code: str, message: str) -> dict[str, JsonValue]:
    return {"error": {"type": kind, "code": code, "message": message}}


def client_error(failure: UpstreamFailure) -> tuple[int, dict[str, JsonValue]]:
    """The OpenAI-shaped error a client receives once recovery reports this failure."""
    message = failure.message
    match failure.kind:
        case "quota":
            payload = _error("usage_limit_reached", "usage_limit_reached", message)
            if failure.reset_at is not None:
                detail = cast(dict[str, JsonValue], payload["error"])
                detail["resets_at"] = math.ceil(failure.reset_at.timestamp())
            return 429, payload
        case "rate_limit":
            return 429, _error("rate_limit_exceeded", "rate_limit_exceeded", message)
        case "unexplained_429":
            return 429, _error(
                "rate_limit_exceeded",
                "antigravity_unexplained_rate_limit",
                "Antigravity answered 429 without quota or rate-limit details. The account's quota may "
                "still remain; the cause is unconfirmed and may be content-based.",
            )
        case "overloaded":
            return 503, _error("server_error", "server_is_overloaded", message)
        case "auth":
            return 502, _error("upstream_error", "antigravity_unauthenticated", "Antigravity rejected the credentials")
        case "banned":
            return 503, _error("server_error", "antigravity_account_banned", message)
        case "verification":
            # The message may carry the verification link and its continuation token.
            return 503, _error(
                "server_error",
                "antigravity_verification_required",
                "Google requires account verification in the official Antigravity app",
            )
        case "permission":
            return 502, _error("upstream_error", "antigravity_permission_denied", message)
        case "location":
            return 503, _error("server_error", "antigravity_location_unsupported", message)
        case "signature":
            return 400, _error("invalid_request_error", "invalid_provider_history", message)
        case "context_length":
            return 400, _error("invalid_request_error", "context_length_exceeded", message)
        case "invalid_request":
            return 400, _error("invalid_request_error", "invalid_request", message)
        case "not_found":
            return 400, _error("invalid_request_error", "model_not_found", message)
        case _:
            return 502, _error("upstream_error", "upstream_error", message)


class AntigravityUpstreamError(ModelSourceForwardingError):
    """A classified Cloud Code rejection; the payload is the client error, never Google's raw body."""

    def __init__(
        self,
        failure: UpstreamFailure,
        *,
        secret: str,
        retry_after: str | None,
        upstream_headers: dict[str, str] | None = None,
    ) -> None:
        status, payload = client_error(failure)
        if retry_after is None and failure.retry_after is not None:
            retry_after = str(max(1, math.ceil(failure.retry_after.total_seconds())))
        super().__init__(
            status_code=status,
            payload=cast(dict[str, JsonValue], _redact_json_value(payload, secret)),
            upstream_status_code=failure.status,
            retry_after=retry_after,
            upstream_headers=upstream_headers,
        )
        self.failure = failure


@dataclass
class RecoveryState:
    """One client request's recovery: what was tried, on which account, and what remains."""

    excluded: set[str] = field(default_factory=set)
    # The account the next attempt must use (same-account retries).
    retry_source_id: str | None = None
    # The access token Google rejected, so the next snapshot refreshes it.
    rejected_token: str | None = field(default=None, repr=False)
    access_token: str | None = field(default=None, repr=False)
    source_id: str | None = None
    generation: int | None = None
    quota_family: QuotaFamily | None = None
    model_family: str | None = None
    sends: int = 0
    stream_opened: bool = False
    same_account_retried: bool = False
    overload_retried: bool = False
    auth_retried: set[str] = field(default_factory=set)
    # After a rejected signature every step is sent unsigned; never repaired twice.
    unsigned: bool = False
    upstream_429s: int = 0
    last_error: ModelSourceForwardingError | None = None

    def bind(
        self, source_id: str, generation: int, access_token: str, quota_family: QuotaFamily, model_family: str
    ) -> None:
        self.source_id = source_id
        self.generation = generation
        self.access_token = access_token
        self.quota_family = quota_family
        self.model_family = model_family
        self.retry_source_id = None
        self.rejected_token = None
        self.sends += 1


def _jitter() -> float:
    return random.uniform(0.25, 2.0)


async def _record(state: RecoveryState, failure: UpstreamFailure) -> None:
    assert state.source_id is not None and state.generation is not None
    async with get_background_session() as session:
        repository = AntigravityRepository(session)
        await record_failure(
            repository,
            state.source_id,
            state.generation,
            failure,
            quota_family=state.quota_family,
            model_family=state.model_family,
        )
        await session.commit()


async def plan_retry(state: RecoveryState, error: ModelSourceForwardingError) -> float | None:
    """Record what the failure proves and return the delay before the next attempt; None reports it."""
    state.last_error = error
    if state.stream_opened or state.sends >= MAX_SENDS:
        return None
    source_id = state.source_id
    assert source_id is not None
    if not isinstance(error, AntigravityUpstreamError):
        # Only a connection that provably sent nothing may be replayed.
        if not error.pre_dispatch or state.same_account_retried:
            return None
        state.same_account_retried = True
        state.retry_source_id = source_id
        logger.info("antigravity_connect_retry source_id=%s", source_id)
        return _jitter()
    failure = error.failure
    kind = failure.kind
    if kind in ("rate_limit", "unexplained_429", "quota"):
        state.upstream_429s += 1
        if state.upstream_429s > MAX_UPSTREAM_429:
            return None
    delay: float | None
    match kind:
        case "quota" | "banned" | "verification" | "not_found" | "permission":
            await _record(state, failure)
            state.excluded.add(source_id)
            delay = 0.0
        case "rate_limit":
            wait = failure.retry_after
            if (wait is None or wait < MOVE_THRESHOLD) and not state.same_account_retried:
                state.same_account_retried = True
                state.retry_source_id = source_id
                delay = max(wait.total_seconds() if wait else 0.0, _jitter())
            else:
                await _record(state, failure)
                state.excluded.add(source_id)
                delay = 0.0
        case "unexplained_429":
            # A content rejection fails identically on every account: never walk the pool.
            if state.same_account_retried:
                return None
            state.same_account_retried = True
            state.retry_source_id = source_id
            hinted = error.retry_after
            delay = max(float(hinted) if hinted is not None and hinted.isdecimal() else 0.0, _jitter())
        case "overloaded" | "transient":
            if state.overload_retried:
                return None
            state.overload_retried = True
            state.excluded.add(source_id)
            delay = _jitter()
        case "auth":
            if source_id in state.auth_retried:
                state.excluded.add(source_id)
                delay = 0.0
            else:
                state.auth_retried.add(source_id)
                state.retry_source_id = source_id
                state.rejected_token = state.access_token
                delay = 0.0
        case "signature":
            if state.unsigned:
                return None
            state.unsigned = True
            state.retry_source_id = source_id
            delay = 0.0
        case "location":
            # The server's egress region applies to every account.
            await _record(state, failure)
            return None
        case _:
            return None
    logger.info(
        "antigravity_recovery source_id=%s failure=%s reason=%s sends=%d excluded=%d delay_ms=%d",
        source_id,
        kind,
        failure.reason,
        state.sends,
        len(state.excluded),
        int(delay * 1000),
    )
    return delay
