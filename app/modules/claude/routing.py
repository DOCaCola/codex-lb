"""Provider-owned Claude selection; authorization precedes affinity.

Selection does not dispatch or retry a request. An unavailable owned model is an
error, never a signal to try a different provider. The transport must revalidate
credentials and acquire source admission before sending any bytes upstream.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ClaudeAccount, ModelSource, ModelSourceModel
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.quota import model_quota, quota_status
from app.modules.claude.schemas import AccountState
from app.modules.model_sources.selection import allowed_source_ids_for_api_key


class ClaudePoolUnavailable(ClaudeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: Literal["ready", "paused", "credentials", "refreshing", "refresh_backoff", "model", "quota"]
    retry_at: datetime | None = None


def eligibility(account: ClaudeAccount, model: str, *, now: datetime) -> Eligibility:
    source = account.source
    if not source.is_enabled:
        return Eligibility(False, "paused")
    if account.credential_status != "ready":
        return Eligibility(False, "credentials")
    if account.refresh_intent is not None:
        return Eligibility(False, "refreshing")
    if account.retry_at is not None and account.retry_at.replace(tzinfo=UTC) > now:
        return Eligibility(False, "refresh_backoff", account.retry_at.replace(tzinfo=UTC))
    if not source.supports_responses or not any(row.model == model and row.is_enabled for row in source.models):
        return Eligibility(False, "model")
    state = AccountState.model_validate_json(account.state_json)
    quota = model_quota(model, quota_status(state, now=now).windows)
    if quota.blocked:
        return Eligibility(False, "quota", quota.retry_at)
    # Expiry alone is not permanent ineligibility: dispatch owns the durable
    # refresh claim. It must never send the expired token itself.
    return Eligibility(True, "ready")


def _score(source_id: str, scope: str, conversation_id: str, model: str) -> bytes:
    values = (scope, conversation_id, model, source_id)
    return hashlib.sha256("".join(f"{len(value)}:{value}" for value in values).encode()).digest()


async def select_account(
    session: AsyncSession,
    model: str,
    api_key: ApiKeyData | None,
    *,
    conversation_id: str,
    owner_source_id: str | None = None,
    excluded_source_ids: frozenset[str] = frozenset(),
    require_streaming: bool = False,
    now: datetime | None = None,
) -> ClaudeAccount:
    now = now or datetime.now(UTC)
    if api_key is not None and (
        (api_key.allowed_models and model not in api_key.allowed_models)
        or (api_key.enforced_model is not None and api_key.enforced_model != model)
    ):
        raise ClaudePoolUnavailable("model_not_allowed", "Claude model is not allowed for this API key")
    allowed = allowed_source_ids_for_api_key(api_key)
    statement = (
        select(ClaudeAccount)
        .options(selectinload(ClaudeAccount.source).selectinload(ModelSource.models))
        .join(ModelSource, ModelSource.id == ClaudeAccount.source_id)
        .join(ModelSourceModel, ModelSourceModel.source_id == ModelSource.id)
        .where(ModelSource.kind == "claude", ModelSourceModel.model == model)
    )
    if allowed is not None:
        statement = statement.where(ModelSource.id.in_(allowed))
    if owner_source_id is not None:
        statement = statement.where(ModelSource.id == owner_source_id)
    if require_streaming:
        statement = statement.where(ModelSourceModel.supports_streaming.is_(True))
    accounts = list((await session.scalars(statement)).unique())
    eligible = [
        account
        for account in accounts
        if account.source_id not in excluded_source_ids and eligibility(account, model, now=now).eligible
    ]
    if not eligible:
        if owner_source_id is not None:
            raise ClaudePoolUnavailable(
                "previous_response_owner_unavailable",
                "Claude continuation owner is unavailable; account-bound state cannot move to another account",
            )
        raise ClaudePoolUnavailable(
            "claude_pool_unavailable", "No authorized Claude account is available for this model"
        )
    scope = api_key.id if api_key else "anonymous"
    return max(eligible, key=lambda account: _score(account.source_id, scope, conversation_id, model))
