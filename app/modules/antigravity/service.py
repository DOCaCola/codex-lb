from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import (
    AccountRoutingPolicy,
    AntigravityAccount,
    AntigravityCooldown,
    AntigravityOAuthFlow,
    AntigravitySessionOwner,
    ModelSource,
    ModelSourceModel,
)
from app.modules.antigravity import oauth
from app.modules.antigravity.auth import AntigravityAuth
from app.modules.antigravity.catalog import default_level, levels, parse_catalog
from app.modules.antigravity.classify import classify
from app.modules.antigravity.client import CloudCodeClient, LoadCodeAssist
from app.modules.antigravity.constants import ANTIGRAVITY_KIND, CLOUD_CODE_BASE_URL, MODEL_PREFIX
from app.modules.antigravity.errors import AntigravityError, MetadataHTTPError
from app.modules.antigravity.failures import record_failure
from app.modules.antigravity.quota import parse_summary, plan_type, quota_weight, window_status
from app.modules.antigravity.repository import AntigravityRepository
from app.modules.antigravity.schemas import (
    AccountState,
    AntigravityAccountResponse,
    AntigravityImport,
    AntigravityReconnect,
    AntigravityUpdate,
    Cooldown,
    Credentials,
    Credit,
    Hold,
    MetadataState,
    OAuthComplete,
    OAuthStart,
    OAuthStarted,
    Subscription,
    Tier,
)
from app.modules.antigravity.version import AntigravityVersionService
from app.modules.model_sources.service import ModelSourceNotFoundError

logger = logging.getLogger(__name__)

Endpoint = Literal["account", "catalog", "quota"]
INTERVALS: dict[Endpoint, timedelta] = {
    "account": timedelta(hours=1),
    "catalog": timedelta(hours=1),
    # The CLI reads the quota summary on every start; a 5-minute poll stays within that pattern.
    "quota": timedelta(minutes=5),
}
FETCH_TIMEOUT_SECONDS = 45
OAUTH_FLOW_TTL = timedelta(minutes=15)


def session_id() -> str:
    """One signed-int64 decimal per account, like one native CLI installation."""
    return str(secrets.randbits(64) - 2**63)


def _due(state: AccountState, endpoint: Endpoint, now: datetime, *, force: bool) -> bool:
    metadata = state.metadata.get(endpoint)
    if metadata is None:
        return True
    if metadata.retry_at is not None and metadata.retry_at > now:
        return False
    if force:
        return True
    return metadata.updated_at is None or now - metadata.updated_at >= INTERVALS[endpoint]


def subscription(load: LoadCodeAssist, now: datetime) -> Subscription:
    paid = load.paid_tier
    return Subscription(
        current_tier=Tier(id=load.current_tier.id, name=load.current_tier.name) if load.current_tier else None,
        paid_tier=Tier(id=paid.id, name=paid.name) if paid else None,
        credits=[
            Credit(
                credit_type=credit.credit_type,
                amount=credit.credit_amount,
                minimum_for_usage=credit.minimum_for_usage,
            )
            for credit in (paid.available_credits if paid else [])
        ],
        observed_at=now,
    )


class AntigravityService:
    def __init__(self, repository: AntigravityRepository) -> None:
        self.repository = repository
        self.encryptor = TokenEncryptor()
        self.auth = AntigravityAuth(repository, self.encryptor)

    async def _get(self, source_id: str) -> AntigravityAccount:
        row = await self.repository.get(source_id)
        if row is None:
            raise ModelSourceNotFoundError("Antigravity account not found")
        return row

    async def _client(self) -> CloudCodeClient:
        return CloudCodeClient(await AntigravityVersionService(self.repository.session).snapshot())

    async def list_accounts(self) -> list[AntigravityAccountResponse]:
        rows = await self.repository.list_accounts()
        cooldowns = await self.repository.cooldowns([row.source_id for row in rows], datetime.now(UTC))
        return [self._response(row, [item for item in cooldowns if item.source_id == row.source_id]) for row in rows]

    async def response(self, source_id: str) -> AntigravityAccountResponse:
        row = await self._get(source_id)
        return self._response(row, await self.repository.cooldowns([source_id], datetime.now(UTC)))

    async def start_oauth(self, payload: OAuthStart) -> OAuthStarted:
        target = await self._get(payload.source_id) if payload.source_id is not None else None
        flow = oauth.PKCE.create()
        expires_at = utcnow() + OAUTH_FLOW_TTL
        await self.repository.session.execute(
            delete(AntigravityOAuthFlow).where(AntigravityOAuthFlow.expires_at <= utcnow())
        )
        self.repository.session.add(
            AntigravityOAuthFlow(
                state_hash=hashlib.sha256(flow.state.encode()).hexdigest(),
                verifier_encrypted=self.encryptor.encrypt(flow.verifier),
                name=payload.name,
                source_id=target.source_id if target else None,
                expires_at=expires_at,
            )
        )
        await self.repository.session.commit()
        return OAuthStarted(
            state=flow.state, authorization_url=flow.authorization_url, expires_at=expires_at.replace(tzinfo=UTC)
        )

    async def complete_oauth(self, payload: OAuthComplete) -> AntigravityAccountResponse:
        # Parse before consuming, and consume before the exchange, so a code is never exchanged twice.
        code = oauth.pasted_code(payload.code.get_secret_value(), payload.state)
        flow = await self.repository.consume_flow(hashlib.sha256(payload.state.encode()).hexdigest())
        if flow is None:
            raise AntigravityError("OAuth flow expired or has already been used")
        credentials = await oauth.exchange(
            oauth.PKCE(payload.state, self.encryptor.decrypt(flow.verifier_encrypted)), code
        )
        if flow.source_id is not None:
            return await self._replace(flow.source_id, credentials)
        return await self._create(flow.name, credentials)

    async def import_account(self, payload: AntigravityImport) -> AntigravityAccountResponse:
        # Only the refresh token is trusted; it must refresh before anything is stored.
        credentials = await oauth.refresh(oauth.imported_refresh_token(payload.credentials))
        return await self._create(payload.name, credentials)

    async def reconnect(self, source_id: str, payload: AntigravityReconnect) -> AntigravityAccountResponse:
        await self._get(source_id)
        credentials = await oauth.refresh(oauth.imported_refresh_token(payload.credentials))
        return await self._replace(source_id, credentials)

    async def _bootstrap(self, credentials: Credentials) -> tuple[str, LoadCodeAssist]:
        """loadCodeAssist and, for a new Google account, onboarding to its managed project."""
        client = await self._client()
        token = credentials.access_token.get_secret_value()
        try:
            load = await client.load_code_assist(token)
            project = load.project or await client.onboard(token, load.onboarding_tier())
        except MetadataHTTPError as exc:
            failure = classify(exc.status, exc.body)
            raise AntigravityError(f"Antigravity refused the account: {failure.message}") from exc
        return project, load

    async def _create(self, name: str, credentials: Credentials) -> AntigravityAccountResponse:
        if not name.strip():
            raise AntigravityError("Account name is required")
        user = await oauth.userinfo(credentials.access_token.get_secret_value())
        if await self.repository.by_subject(user.id) is not None:
            raise AntigravityError("This Google account is already enrolled; reconnect it instead")
        project, load = await self._bootstrap(credentials)
        now = datetime.now(UTC)
        source = ModelSource(
            id=f"src_{uuid.uuid4().hex}",
            name=name.strip(),
            kind=ANTIGRAVITY_KIND,
            base_url=CLOUD_CODE_BASE_URL,
            api_key_encrypted=None,
            # Google names third-party use of this login as grounds for suspension: the operator enables it.
            is_enabled=False,
            health_status="unknown",
            supports_responses=True,
            supports_chat_completions=False,
            supports_audio_transcriptions=False,
            supports_embeddings=False,
            models=[],
        )
        state = AccountState(subscription=subscription(load, now), metadata={"account": MetadataState(updated_at=now)})
        row = AntigravityAccount(
            source_id=source.id,
            source=source,
            credentials_encrypted=oauth.encrypt_credentials(credentials, self.encryptor),
            google_subject=user.id,
            email=user.email,
            project_id=project,
            session_id=session_id(),
            expires_at=credentials.expires_at.replace(tzinfo=None),
            credential_status="ready",
            state_json=state.model_dump_json(),
        )
        self.repository.session.add(row)
        try:
            await self.repository.session.commit()
        except IntegrityError as exc:
            await self.repository.session.rollback()
            raise AntigravityError("This Google account is already enrolled; reconnect it instead") from exc
        logger.info("antigravity_account_created source_id=%s", source.id)
        # Bootstrap just loaded the account; only the catalog and quota are due.
        return await self.refresh(source.id, force=False)

    async def _replace(self, source_id: str, credentials: Credentials) -> AntigravityAccountResponse:
        """Reconnect by Google subject; a plan change on the same subject updates in place."""
        row = await self._get(source_id)
        user = await oauth.userinfo(credentials.access_token.get_secret_value())
        if user.id != row.google_subject:
            logger.warning("antigravity_reconnect_rejected source_id=%s reason=subject_mismatch", source_id)
            raise AntigravityError(
                "Reconnect authenticated a different Google account. Sign in with the original account "
                "or add this one separately. Existing credentials were not replaced.",
                code="antigravity_identity_mismatch",
            )
        project, load = await self._bootstrap(credentials)
        generation = row.generation
        now = datetime.now(UTC)
        changed = await self.repository.update_account(
            source_id,
            generation,
            credentials_encrypted=oauth.encrypt_credentials(credentials, self.encryptor),
            expires_at=credentials.expires_at.replace(tzinfo=None),
            email=user.email,
            project_id=project,
            credential_status="ready",
            retry_at=None,
            generation=generation + 1,
        )
        if not changed:
            raise AntigravityError("Antigravity account changed during reconnect; retry")

        def refreshed(state: AccountState) -> AccountState:
            state.subscription = subscription(load, now)
            state.metadata = {"account": MetadataState(updated_at=now)}
            state.verification = None
            return state

        await self.repository.mutate_state(source_id, generation + 1, refreshed)
        await self.repository.clear_cooldowns(source_id)
        await self.repository.session.commit()
        logger.info("antigravity_account_reconnected source_id=%s generation=%d", source_id, generation + 1)
        return await self.refresh(source_id, force=False)

    async def update(self, source_id: str, payload: AntigravityUpdate) -> AntigravityAccountResponse:
        row = await self._get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        if payload.name is not None:
            if not payload.name.strip():
                raise AntigravityError("Account name is required")
            row.source.name = payload.name.strip()
        if payload.is_enabled is not None:
            if payload.is_enabled and row.hold is not None:
                raise AntigravityError("Clear the account hold before enabling it")
            row.source.is_enabled = payload.is_enabled
        if payload.routing_policy is not None:
            row.routing_policy = payload.routing_policy.value
        if "max_concurrency" in payload.model_fields_set:
            row.source.max_concurrency = payload.max_concurrency
        if payload.clear_hold:
            row.hold = None
            row.hold_reason = None
            row.hold_at = None
        project = payload.all_models is not None or payload.selections is not None
        if payload.all_models is not None:
            state.all_models = payload.all_models
        if payload.selections is not None:
            known = {family.id for family in state.catalog} | set(state.selections)
            if len(payload.selections) != len(set(payload.selections)) or set(payload.selections) - known:
                raise AntigravityError("Select each model once from the synchronized catalog")
            state.selections = payload.selections
        if project:
            selected_all, selections = state.all_models, state.selections

            def choose(current: AccountState) -> AccountState:
                current.all_models = selected_all
                current.selections = selections
                return current

            merged = await self.repository.mutate_state(source_id, row.generation, choose)
            if merged is None:
                raise AntigravityError("Antigravity account changed during update; reload and retry")
            await self.repository.sources.replace_models(row.source, project_models(merged), commit=False)
        await self.repository.session.commit()
        return await self.response(source_id)

    async def refresh(self, source_id: str, *, force: bool = True) -> AntigravityAccountResponse:
        row = await self._get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        now = datetime.now(UTC)
        due = [endpoint for endpoint in INTERVALS if _due(state, endpoint, now, force=force)]
        if row.project_id is None and "account" not in due:
            due.insert(0, "account")
        # A banned account sends nothing; a credential problem waits for reconnect.
        if not due or row.hold == "banned" or row.credential_status != "ready":
            return await self.response(source_id)
        snapshot = await self.auth.snapshot(source_id)
        client = await self._client()
        generation = snapshot.generation
        project = snapshot.project_id
        for endpoint in due:
            if endpoint != "account" and project is None:
                break
            error: str | None = None
            retry_at: datetime | None = None
            completed_at = datetime.now(UTC)
            try:
                async with asyncio.timeout(FETCH_TIMEOUT_SECONDS):
                    if endpoint == "account":
                        load = await client.load_code_assist(snapshot.access_token)
                        project = load.project or await client.onboard(snapshot.access_token, load.onboarding_tier())
                        values: dict[str, object] = {"project_id": project}
                        if row.hold == "misconfigured":
                            values.update(hold=None, hold_reason=None, hold_at=None)
                        await self.repository.update_account(source_id, generation, **values)
                        observed = subscription(load, completed_at)

                        def store_subscription(current: AccountState) -> AccountState:
                            current.subscription = observed
                            return current

                        await self.repository.mutate_state(source_id, generation, store_subscription)
                    elif endpoint == "catalog":
                        assert project is not None
                        families, default = parse_catalog(await client.available_models(snapshot.access_token, project))

                        def store_catalog(current: AccountState) -> AccountState:
                            current.catalog = families
                            current.default_model = default
                            return current

                        merged = await self.repository.mutate_state(source_id, generation, store_catalog)
                        if merged is not None:
                            current_row = await self._get(source_id)
                            await self.repository.sources.replace_models(
                                current_row.source, project_models(merged), commit=False
                            )
                    else:
                        assert project is not None
                        buckets = parse_summary(await client.quota_summary(snapshot.access_token, project))

                        def store_quota(current: AccountState) -> AccountState:
                            current.quota = buckets
                            current.verification = None
                            return current

                        await self.repository.mutate_state(source_id, generation, store_quota)
                        await self.repository.record_quota(source_id, buckets, completed_at)
            except MetadataHTTPError as exc:
                failure = classify(exc.status, exc.body)
                error = f"{endpoint}: {failure.message}"
                retry_at = exc.retry_at if exc.status == 429 else completed_at + INTERVALS[endpoint]
                await record_failure(self.repository, source_id, generation, failure)
                if failure.kind == "permission" and endpoint == "account":
                    await self.repository.update_account(
                        source_id, generation, hold="misconfigured", hold_reason=failure.message, hold_at=utcnow()
                    )
            except (AntigravityError, TimeoutError) as exc:
                error = str(exc) if isinstance(exc, AntigravityError) else f"Antigravity {endpoint} timed out"
                retry_at = completed_at + INTERVALS[endpoint]
            result = MetadataState(
                updated_at=completed_at
                if error is None
                else (state.metadata.get(endpoint) or MetadataState()).updated_at,
                error=error,
                retry_at=retry_at,
            )

            def store_metadata(current: AccountState, endpoint: Endpoint = endpoint) -> AccountState:
                current.metadata[endpoint] = result
                return current

            await self.repository.mutate_state(source_id, generation, store_metadata)
            await self.repository.session.commit()
            if error is not None:
                logger.warning("antigravity_metadata_refresh_failed source_id=%s endpoint=%s", source_id, endpoint)
                if endpoint == "account":
                    break
        return await self.response(source_id)

    async def delete(self, source_id: str) -> None:
        await self._get(source_id)
        await self.repository.session.execute(
            delete(AntigravitySessionOwner).where(AntigravitySessionOwner.source_id == source_id)
        )
        await self.repository.sources.delete(source_id)

    @staticmethod
    def _response(row: AntigravityAccount, cooldowns: list[AntigravityCooldown]) -> AntigravityAccountResponse:
        state = AccountState.model_validate_json(row.state_json)
        plan = plan_type(state.subscription)
        return AntigravityAccountResponse(
            id=row.source_id,
            name=row.source.name,
            email=row.email,
            project_id=row.project_id,
            is_enabled=row.source.is_enabled,
            routing_policy=AccountRoutingPolicy(row.routing_policy),
            max_concurrency=row.source.max_concurrency,
            credential_status=row.credential_status,
            hold=cast(Hold | None, row.hold),
            hold_reason=row.hold_reason,
            hold_at=row.hold_at.replace(tzinfo=UTC) if row.hold_at else None,
            expires_at=row.expires_at.replace(tzinfo=UTC),
            plan_type=plan,
            quota_weight=quota_weight(plan),
            state=state,
            windows=window_status(state, datetime.now(UTC)),
            cooldowns=[
                Cooldown(scope=item.scope, until=item.until.replace(tzinfo=UTC), reason=item.reason)
                for item in cooldowns
            ],
        )


def selected_families(state: AccountState) -> list[str]:
    return [family.id for family in state.catalog] if state.all_models else list(state.selections)


def project_models(state: AccountState) -> list[ModelSourceModel]:
    from app.core.usage.pricing import get_pricing_for_model

    catalog = {family.id: family for family in state.catalog}
    result: list[ModelSourceModel] = []
    for family_id in selected_families(state):
        family = catalog.get(family_id)
        if family is None:
            continue
        resolved = get_pricing_for_model(family.id)
        price = resolved[1] if resolved is not None else None
        tiers = levels(family)
        result.append(
            ModelSourceModel(
                model=MODEL_PREFIX + family.id,
                display_name=family.display_name,
                context_window=family.context_window,
                max_output_tokens=family.max_output_tokens,
                is_enabled=family.max_output_tokens is not None,
                supports_streaming=True,
                supports_tools=True,
                supports_vision=family.supports_images,
                input_per_1m=price.input_per_1m if price is not None else None,
                cached_input_per_1m=price.cached_input_per_1m if price is not None else None,
                output_per_1m=price.output_per_1m if price is not None else None,
                raw_metadata_json=json.dumps(
                    {
                        "upstream_model": family.id,
                        "quota_family": family.quota_family,
                        "supports_reasoning": bool(tiers),
                        "supported_reasoning_levels": list(tiers),
                        "default_reasoning_level": default_level(family),
                    }
                ),
            )
        )
    return result
