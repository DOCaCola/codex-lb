"""Request-wide send budget and persistent scoped upstream refusal policy."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Literal

from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.crypto import TokenEncryptor
from app.db.models import ClaudeCooldown
from app.db.session import get_background_session
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.auth import ClaudeAuth
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.routing import select_account
from app.modules.model_sources.forwarding import ModelSourceForwardingError

logger = logging.getLogger(__name__)


@dataclass
class SendBudget:
    remaining: int = 4

    def consume(self) -> None:
        if self.remaining <= 0:
            raise RuntimeError("Claude send budget exhausted before dispatch")
        self.remaining -= 1


@dataclass
class FailoverState:
    budget: SendBudget = field(default_factory=SendBudget)
    excluded: set[str] = field(default_factory=set)
    source_id: str | None = None
    last_error: ModelSourceForwardingError | None = None
    stream_opened: bool = False
    credential_generation: int | None = None
    auth_retried: set[str] = field(default_factory=set)
    retry_source_id: str | None = None


def is_authentication_failure(error: ModelSourceForwardingError) -> bool:
    if error.upstream_status_code != 401:
        return False
    detail = error.payload.get("error")
    return isinstance(detail, dict) and detail.get("type") in (None, "authentication_error")


async def recover_authentication(state: FailoverState, model: str, api_key: ApiKeyData | None) -> None:
    assert state.source_id is not None and state.credential_generation is not None
    source_id = state.source_id
    state.retry_source_id = None
    async with get_background_session() as session:
        repository = ClaudeRepository(session)
        if source_id in state.auth_retried:
            await repository.backoff_rejected_generation(
                source_id, state.credential_generation, datetime.now(UTC).replace(tzinfo=None)
            )
            state.excluded.add(source_id)
            logger.info("claude_auth_recovery source_id=%s outcome=rejected_again", source_id)
            return
        if state.budget.remaining == 0:
            return
        state.auth_retried.add(source_id)
        try:
            # Authorization and current eligibility still precede refresh.
            await select_account(session, model, api_key, conversation_id="", owner_source_id=source_id)
            await ClaudeAuth(repository, ClaudeClient(), TokenEncryptor()).snapshot(
                source_id, rejected_generation=state.credential_generation
            )
        except ClaudeError:
            # Auth owns terminal/backoff/uncertain state. Never rewrite it here.
            state.excluded.add(source_id)
            logger.info("claude_auth_recovery source_id=%s outcome=unavailable", source_id)
            return
    state.retry_source_id = source_id
    logger.info("claude_auth_recovery source_id=%s outcome=reprepare", source_id)


@dataclass(frozen=True)
class Refusal:
    scope: Literal["account", "model"]
    until: datetime
    reason: Literal["retry_after", "reset", "default"]


def classify_refusal(error: ModelSourceForwardingError, *, now: datetime) -> Refusal | None:
    if error.upstream_status_code != 429:
        return None
    detail = error.payload.get("error")
    message = detail.get("message") if isinstance(detail, dict) else None
    message = message.lower() if isinstance(message, str) else ""
    if "fast request rejected" in message or (
        "fast" in message and ("usage credits" in message or "credits are required" in message)
    ):
        return None
    headers = {key.lower(): value for key, value in error.upstream_headers.items()}
    rejected = [
        prefix
        for prefix in ("anthropic-ratelimit-unified-5h", "anthropic-ratelimit-unified-7d")
        if headers.get(prefix + "-status") == "rejected"
    ]
    unified = headers.get("anthropic-ratelimit-unified-status") == "rejected"
    scope: Literal["account", "model"] = "account" if rejected or unified else "model"
    retry = error.retry_after or headers.get("retry-after")
    if retry:
        try:
            seconds = float(retry)
            deadline = now + timedelta(seconds=max(1, seconds)) if math.isfinite(seconds) else None
        except (ValueError, OverflowError):
            try:
                deadline = parsedate_to_datetime(retry).astimezone(UTC)
            except (ValueError, TypeError, OverflowError):
                deadline = None
        if deadline is not None and deadline > now:
            return Refusal(scope, deadline, "retry_after")
    resets: list[datetime] = []
    for prefix in rejected or (["anthropic-ratelimit-unified"] if unified else []):
        value = headers.get(prefix + "-reset")
        if value is None:
            continue
        try:
            deadline = datetime.fromtimestamp(float(value), UTC)
        except (ValueError, OverflowError, OSError):
            continue
        if deadline > now:
            resets.append(deadline)
    if resets:
        return Refusal(scope, max(resets), "reset")
    return Refusal(scope, now + timedelta(seconds=60), "default")


async def record_refusal(source_id: str, model: str, refusal: Refusal) -> None:
    until = refusal.until.astimezone(UTC).replace(tzinfo=None)
    async with get_background_session() as session:
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        statement = insert(ClaudeCooldown).values(
            source_id=source_id, model="*" if refusal.scope == "account" else model, until=until
        )
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[ClaudeCooldown.source_id, ClaudeCooldown.model],
                set_={"until": case((ClaudeCooldown.until > until, ClaudeCooldown.until), else_=until)},
            )
        )
        await session.commit()
    logger.info("claude_refusal source_id=%s scope=%s cooldown=%s", source_id, refusal.scope, refusal.reason)
