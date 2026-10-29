"""Antigravity account selection: eligibility, conversation stickiness and the shared strategy.

A conversation stays on its account (same project, signatures and Google-side
cache); it moves only when that account cannot serve the model. Selection never
dispatches or retries; the recovery loop decides what a failure permits.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.balancer import AccountState as Candidate
from app.core.balancer import ResetPreferenceWindow, RoutingStrategy
from app.core.balancer import select_account as select_candidate
from app.core.config.settings_cache import get_settings_cache
from app.core.errors import OpenAIErrorDetail
from app.core.routing_diagnostics import RoutingExclusion, explain_unavailable
from app.core.utils.time import utcnow
from app.db.models import (
    AccountStatus,
    AntigravityAccount,
    AntigravityCooldown,
    AntigravitySessionOwner,
    DashboardSettings,
    ModelSource,
    ModelSourceModel,
)
from app.modules.antigravity.constants import ANTIGRAVITY_KIND, MODEL_PREFIX
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.failures import ACCOUNT_SCOPE, family_scope, model_scope
from app.modules.antigravity.quota import family_quota, plan_type, quota_weight
from app.modules.antigravity.schemas import AccountState, CatalogFamily
from app.modules.api_keys.service import ApiKeyData
from app.modules.model_sources.selection import allowed_source_ids_for_api_key

SESSION_TTL = timedelta(hours=1)


class AntigravityPoolUnavailable(AntigravityError):
    def __init__(self, code: str, message: str, *, status_code: int = 503, retry_at: datetime | None = None) -> None:
        super().__init__(message, code=code, status_code=status_code)
        self.retry_at = retry_at

    @property
    def response_headers(self) -> dict[str, str]:
        if self.retry_at is None:
            return {}
        return {"Retry-After": str(max(1, math.ceil((self.retry_at - datetime.now(UTC)).total_seconds())))}

    @property
    def responses_error_detail(self) -> OpenAIErrorDetail:
        detail = super().responses_error_detail
        if self.status_code == 429:
            # Codex shows only this type as a usage limit with its reset time.
            detail["type"] = "usage_limit_reached"
        if self.retry_at is not None:
            detail["resets_at"] = math.ceil(self.retry_at.timestamp())
            detail["resets_in_seconds"] = int(self.response_headers["Retry-After"])
        return detail


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: RoutingExclusion | None
    retry_at: datetime | None = None


def catalog_family(account: AntigravityAccount, model: str) -> CatalogFamily | None:
    family_id = model.removeprefix(MODEL_PREFIX)
    state = AccountState.model_validate_json(account.state_json)
    return next((family for family in state.catalog if family.id == family_id), None)


def eligibility(
    account: AntigravityAccount, model: str, *, now: datetime, cooldowns: Sequence[AntigravityCooldown] = ()
) -> Eligibility:
    if not account.source.is_enabled:
        return Eligibility(False, "paused")
    if account.hold is not None:
        return Eligibility(False, "deactivated")
    if account.credential_status != "ready":
        return Eligibility(False, "credentials")
    family = catalog_family(account, model)
    if family is None or not any(row.model == model and row.is_enabled for row in account.source.models):
        return Eligibility(False, "model")
    if account.retry_at is not None and account.retry_at.replace(tzinfo=UTC) > now:
        return Eligibility(False, "refresh_backoff", account.retry_at.replace(tzinfo=UTC))
    active = {row.scope: row.until.replace(tzinfo=UTC) for row in cooldowns if row.until.replace(tzinfo=UTC) > now}
    quota = family_quota(AccountState.model_validate_json(account.state_json), family.quota_family, now)
    if family_scope(family.quota_family) in active or quota.blocked:
        deadlines = [until for scope, until in active.items() if scope == family_scope(family.quota_family)]
        if quota.retry_at is not None:
            deadlines.append(quota.retry_at)
        return Eligibility(False, "quota", max(deadlines) if deadlines else None)
    blocking = [active[scope] for scope in (ACCOUNT_SCOPE, model_scope(family.id)) if scope in active]
    if blocking:
        return Eligibility(False, "cooldown", max(blocking))
    return Eligibility(True, None)


def _owner_key(client_scope: str, conversation_id: str) -> str:
    # Model-independent: a model switch inside Antigravity keeps the project and its cache.
    return hashlib.sha256(json.dumps(["antigravity", client_scope, conversation_id]).encode()).hexdigest()


async def session_owner(session: AsyncSession, client_scope: str, conversation_id: str) -> str | None:
    row = await session.get(AntigravitySessionOwner, _owner_key(client_scope, conversation_id), populate_existing=True)
    return row.source_id if row is not None and row.expires_at > utcnow() else None


async def claim_session(session: AsyncSession, client_scope: str, conversation_id: str, source_id: str) -> None:
    """Bind the conversation to the account that serves it; only affinity, never history."""
    now = utcnow()
    key = _owner_key(client_scope, conversation_id)
    await session.execute(delete(AntigravitySessionOwner).where(AntigravitySessionOwner.expires_at <= now))
    row = await session.get(AntigravitySessionOwner, key)
    if row is None:
        session.add(AntigravitySessionOwner(scope_hash=key, source_id=source_id, expires_at=now + SESSION_TTL))
    else:
        row.source_id = source_id
        row.expires_at = now + SESSION_TTL
    await session.execute(
        update(AntigravityAccount).where(AntigravityAccount.source_id == source_id).values(last_selected_at=now)
    )


async def select_account(
    session: AsyncSession,
    model: str,
    api_key: ApiKeyData | None,
    *,
    conversation_id: str,
    excluded_source_ids: frozenset[str] = frozenset(),
    preferred_source_id: str | None = None,
    now: datetime | None = None,
) -> AntigravityAccount:
    now = now or datetime.now(UTC)
    if api_key is not None and (
        (api_key.allowed_models and model not in api_key.allowed_models)
        or (api_key.enforced_model is not None and api_key.enforced_model != model)
    ):
        raise AntigravityPoolUnavailable(
            "model_not_allowed", "Antigravity model is not allowed for this API key", status_code=400
        )
    settings = await get_settings_cache().get()
    target = None
    if settings.routing_strategy == "single_account":
        target = settings.antigravity_single_account_id
        if not target:
            raise AntigravityPoolUnavailable(
                "antigravity_single_account_missing",
                "Select an Antigravity account for single-account routing",
                status_code=400,
            )
    statement = (
        select(AntigravityAccount)
        .options(selectinload(AntigravityAccount.source).selectinload(ModelSource.models))
        .join(ModelSource, ModelSource.id == AntigravityAccount.source_id)
        .join(ModelSourceModel, ModelSourceModel.source_id == ModelSource.id)
        .where(ModelSource.kind == ANTIGRAVITY_KIND, ModelSourceModel.model == model)
    )
    allowed = allowed_source_ids_for_api_key(api_key)
    if allowed is not None:
        statement = statement.where(ModelSource.id.in_(allowed))
    if target is not None:
        statement = statement.where(ModelSource.id == target)
    accounts = list((await session.scalars(statement)).unique())
    cooldowns = list(
        await session.scalars(
            select(AntigravityCooldown).where(
                AntigravityCooldown.source_id.in_([account.source_id for account in accounts]),
                AntigravityCooldown.until > now.replace(tzinfo=None),
            )
        )
    )
    diagnostics = [
        (
            account,
            eligibility(
                account, model, now=now, cooldowns=[row for row in cooldowns if row.source_id == account.source_id]
            ),
        )
        for account in accounts
        if account.source_id not in excluded_source_ids
    ]
    eligible = [account for account, diagnostic in diagnostics if diagnostic.eligible]
    if not eligible:
        reasons: list[RoutingExclusion] = [
            diagnostic.reason for _, diagnostic in diagnostics if diagnostic.reason is not None
        ]
        reasons.extend("excluded" for account in accounts if account.source_id in excluded_source_ids)
        retry_at = min((diagnostic.retry_at for _, diagnostic in diagnostics if diagnostic.retry_at), default=None)
        quota_only = bool(reasons) and all(reason == "quota" for reason in reasons)
        operator_action = bool(reasons) and all(
            reason in {"paused", "credentials", "model", "deactivated"} for reason in reasons
        )
        raise AntigravityPoolUnavailable(
            "antigravity_pool_rate_limited" if quota_only else "antigravity_pool_unavailable",
            explain_unavailable(
                "All authorized Antigravity accounts for this model have exhausted their quota"
                if quota_only
                else "No authorized Antigravity account is available for this model",
                reasons,
                retry_at=retry_at.timestamp() if retry_at is not None else None,
            ),
            status_code=429 if quota_only else 400 if operator_action else 503,
            retry_at=retry_at,
        )
    scope = api_key.id if api_key else "anonymous"
    for owner in (await session_owner(session, scope, conversation_id), preferred_source_id):
        chosen = next((account for account in eligible if account.source_id == owner), None)
        if chosen is not None:
            return chosen
    return choose(eligible, settings, model=model, now=now, seed=json.dumps([scope, conversation_id]))


def choose(
    accounts: list[AntigravityAccount], settings: DashboardSettings, *, model: str, now: datetime, seed: str
) -> AntigravityAccount:
    candidates: list[Candidate] = []
    for account in accounts:
        state = AccountState.model_validate_json(account.state_json)
        family = catalog_family(account, model)
        assert family is not None  # Eligibility requires the catalog family.
        quota = family_quota(state, family.quota_family, now)
        primary, secondary = quota.five_hour, quota.weekly
        candidates.append(
            Candidate(
                account_id=account.source_id,
                routing_policy=account.routing_policy,
                status=AccountStatus.ACTIVE,
                used_percent=primary.used_percent if primary else None,
                primary_reset_at=int(primary.resets_at.timestamp()) if primary and primary.resets_at else None,
                primary_window_minutes=300,
                secondary_used_percent=secondary.used_percent if secondary else None,
                secondary_reset_at=int(secondary.resets_at.timestamp()) if secondary and secondary.resets_at else None,
                capacity_credits=float(quota_weight(plan_type(state.subscription)) or 1),
                last_selected_at=account.last_selected_at.replace(tzinfo=UTC).timestamp()
                if account.last_selected_at
                else None,
            )
        )
    result = select_candidate(
        candidates,
        now=now.timestamp(),
        routing_strategy=cast(RoutingStrategy, settings.routing_strategy),
        prefer_earlier_reset=settings.prefer_earlier_reset_accounts,
        prefer_earlier_reset_window=cast(ResetPreferenceWindow, settings.prefer_earlier_reset_window),
        relative_availability_power=settings.relative_availability_power,
        relative_availability_top_k=settings.relative_availability_top_k,
        allow_backoff_fallback=False,
        selection_seed=seed,
    )
    assert result.account is not None  # Eligibility already admitted this nonempty pool.
    return next(account for account in accounts if account.source_id == result.account.account_id)
