from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import AccountRoutingPolicy, ClaudeAccount, ClaudeOAuthFlow, ModelSource, ModelSourceModel
from app.modules.claude.auth import ClaudeAuth, grant_fingerprint
from app.modules.claude.capabilities import model_policy
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import PKCE, ClaudeError, encrypt_credentials
from app.modules.claude.identity import authenticated_identity
from app.modules.claude.metadata import (
    CLAIM_LEASE,
    FETCH_TIMEOUT_SECONDS,
    USAGE_INTERVAL,
    MetadataHTTPError,
    refresh_due,
)
from app.modules.claude.quota import quota_status
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import (
    CLAUDE_BASE_URL,
    CLAUDE_KIND,
    AccountState,
    CatalogModel,
    ClaudeAccountResponse,
    ClaudeImport,
    ClaudeReconnect,
    ClaudeUpdate,
    Credentials,
    MetadataEndpoint,
    MetadataRefreshState,
    OAuthComplete,
    OAuthStart,
    OAuthStarted,
    UsageSnapshot,
)
from app.modules.claude.version import ClaudeVersionService
from app.modules.model_sources.service import ModelSourceNotFoundError


class ClaudeService:
    def __init__(self, repository: ClaudeRepository, client: ClaudeClient | None = None) -> None:
        self.repository = repository
        self.client = client or ClaudeClient()
        self.encryptor = TokenEncryptor()
        self.auth = ClaudeAuth(repository, self.client, self.encryptor)

    async def _get(self, source_id: str) -> ClaudeAccount:
        row = await self.repository.get(source_id)
        if row is None:
            raise ModelSourceNotFoundError("Claude account not found")
        return row

    async def list_accounts(self) -> list[ClaudeAccountResponse]:
        return [self._response(row) for row in await self.repository.list_accounts()]

    async def import_account(self, payload: ClaudeImport) -> ClaudeAccountResponse:
        return await self._create(payload.name, payload.credentials.claudeAiOauth.credentials())

    async def start_oauth(self, payload: OAuthStart) -> OAuthStarted:
        target = await self._get(payload.source_id) if payload.source_id is not None else None
        flow = PKCE.create()
        expires_at = utcnow() + timedelta(minutes=15)
        await self.repository.session.execute(delete(ClaudeOAuthFlow).where(ClaudeOAuthFlow.expires_at <= utcnow()))
        self.repository.session.add(
            ClaudeOAuthFlow(
                state_hash=hashlib.sha256(flow.state.encode()).hexdigest(),
                verifier_encrypted=self.encryptor.encrypt(flow.verifier),
                name=payload.name,
                source_id=target.source_id if target else None,
                generation=target.generation if target else None,
                expires_at=expires_at,
            )
        )
        await self.repository.session.commit()
        return OAuthStarted(
            state=flow.state, authorization_url=flow.authorization_url, expires_at=expires_at.replace(tzinfo=UTC)
        )

    async def complete_oauth(self, payload: OAuthComplete) -> ClaudeAccountResponse:
        # Validate the returned state before consuming; consume before network
        # dispatch so even a worker restart cannot exchange the same code twice.
        code = payload.code.get_secret_value()
        PKCE(payload.state, "").exchange_body(code)
        flow = await self.repository.consume_flow(hashlib.sha256(payload.state.encode()).hexdigest(), utcnow())
        if flow is None:
            raise ClaudeError("OAuth flow expired or has already been used")
        credentials = await self.client.exchange(
            PKCE(payload.state, self.encryptor.decrypt(flow.verifier_encrypted)), code
        )
        if flow.source_id is not None:
            assert flow.generation is not None
            return await self._replace(flow.source_id, flow.generation, credentials)
        return await self._create(flow.name, credentials)

    async def _create(self, name: str, credentials: Credentials) -> ClaudeAccountResponse:
        if not name.strip():
            raise ClaudeError("Account name is required")
        identity = (
            await authenticated_identity(self.client, self.repository, credentials)
            if credentials.expires_at > datetime.now(UTC)
            else None
        )
        source = ModelSource(
            id=f"src_{uuid.uuid4().hex}",
            name=name.strip(),
            kind=CLAUDE_KIND,
            base_url=CLAUDE_BASE_URL,
            api_key_encrypted=None,
            is_enabled=True,
            health_status="unknown",
            supports_responses=True,
            supports_chat_completions=False,
            supports_audio_transcriptions=False,
            supports_embeddings=False,
            models=[],
        )
        row = ClaudeAccount(
            source_id=source.id,
            source=source,
            credentials_encrypted=encrypt_credentials(credentials, self.encryptor),
            grant_fingerprint=grant_fingerprint(credentials),
            identity_fingerprint=identity,
            expires_at=credentials.expires_at.replace(tzinfo=None),
            credential_status="ready",
            state_json=AccountState().model_dump_json(),
        )
        self.repository.session.add(row)
        try:
            await self.repository.session.commit()
        except IntegrityError as exc:
            await self.repository.session.rollback()
            raise ClaudeError("This Claude grant or authenticated account is already imported") from exc
        return self._response(row)

    async def reconnect(self, source_id: str, payload: ClaudeReconnect) -> ClaudeAccountResponse:
        row = await self._get(source_id)
        return await self._replace(source_id, row.generation, payload.credentials.claudeAiOauth.credentials())

    async def _replace(self, source_id: str, generation: int, credentials: Credentials) -> ClaudeAccountResponse:
        row = await self._get(source_id)
        if row.identity_fingerprint is None:
            raise ClaudeError(
                "Account identity has not been verified; refresh it before reconnecting, or remove it and enroll again"
            )
        if credentials.expires_at <= datetime.now(UTC):
            raise ClaudeError("Reconnect requires a current credential file or a new OAuth sign-in")
        identity = await authenticated_identity(self.client, self.repository, credentials)
        if identity != row.identity_fingerprint:
            raise ClaudeError("Reconnect must use the same authenticated Claude account and organization")
        try:
            changed = await self.repository.session.scalar(
                update(ClaudeAccount)
                .where(
                    ClaudeAccount.source_id == source_id,
                    ClaudeAccount.generation == generation,
                    ClaudeAccount.identity_fingerprint == identity,
                )
                .values(
                    credentials_encrypted=encrypt_credentials(credentials, self.encryptor),
                    grant_fingerprint=grant_fingerprint(credentials),
                    expires_at=credentials.expires_at.replace(tzinfo=None),
                    credential_status="ready",
                    generation=generation + 1,
                    version=ClaudeAccount.version + 1,
                    refresh_intent=None,
                    refresh_started_at=None,
                    retry_at=None,
                )
                .returning(ClaudeAccount.source_id)
                .execution_options(synchronize_session=False)
            )
            await self.repository.session.commit()
        except IntegrityError as exc:
            await self.repository.session.rollback()
            raise ClaudeError("The replacement grant is already enrolled") from exc
        if changed is None:
            raise ClaudeError("Claude credentials changed during reconnect; start a new enrollment")
        return self._response(await self._get(source_id))

    async def update(self, source_id: str, payload: ClaudeUpdate) -> ClaudeAccountResponse:
        row = await self._get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        if payload.name is not None:
            if not payload.name.strip():
                raise ClaudeError("Account name is required")
            row.source.name = payload.name.strip()
        if payload.is_enabled is not None:
            row.source.is_enabled = payload.is_enabled
        if payload.routing_policy is not None:
            row.routing_policy = payload.routing_policy.value
        if "max_concurrency" in payload.model_fields_set:
            row.source.max_concurrency = payload.max_concurrency
        if payload.selections is not None:
            selected = [item.model for item in payload.selections]
            known = {item.id for item in state.catalog} | {item.model for item in state.selections}
            if len(selected) != len(set(selected)) or set(selected) - known:
                raise ClaudeError("Select each model once from the synchronized catalog")
            newly_selected = set(selected) - {item.model for item in state.selections}
            if any(item.id in newly_selected and item.token_limits is None for item in state.catalog):
                raise ClaudeError("Model token limits are unavailable; refresh the catalog before selecting this model")
            state.selections = payload.selections
        await self._save(row, state, project=payload.selections is not None)
        return self._response(row)

    async def refresh(self, source_id: str, *, catalog: bool = True, force: bool = True) -> ClaudeAccountResponse:
        row = await self._get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        endpoints: list[MetadataEndpoint] = ["catalog", "usage"] if catalog else ["usage"]
        refresh_started_at = datetime.now(UTC)
        if not any(refresh_due(state, endpoint, refresh_started_at, force=force) for endpoint in endpoints):
            return self._response(row)
        snapshot = await self.auth.snapshot(source_id)
        identity = await ClaudeVersionService(self.repository.session).snapshot()
        for endpoint in endpoints:
            await self._refresh_endpoint(
                source_id,
                snapshot.generation,
                endpoint,
                snapshot.credentials.access_token.get_secret_value(),
                identity.version,
                force=force,
                refresh_started_at=refresh_started_at,
            )
        return self._response(await self._get(source_id))

    async def _refresh_endpoint(
        self,
        source_id: str,
        generation: int,
        endpoint: MetadataEndpoint,
        token: str,
        version: str,
        *,
        force: bool,
        refresh_started_at: datetime,
    ) -> None:
        operation_id = uuid.uuid4().hex
        requested_at = datetime.now(UTC)

        def claim(state: AccountState) -> AccountState | None:
            updated = state.catalog_updated_at if endpoint == "catalog" else state.usage_updated_at
            if updated is not None and updated >= refresh_started_at:
                return None
            if not refresh_due(state, endpoint, requested_at, force=force):
                return None
            state.metadata_refresh[endpoint] = MetadataRefreshState(
                operation_id=operation_id,
                lease_until=requested_at + CLAIM_LEASE,
            )
            return state

        claimed = await self.repository.mutate_state(source_id, generation, claim)
        # Release the transaction before any network I/O, including on a no-op.
        await self.repository.session.commit()
        if claimed is None:
            return
        result: list[CatalogModel] | UsageSnapshot | None = None
        error: str | None = None
        retry_at: datetime | None = None
        try:
            async with asyncio.timeout(FETCH_TIMEOUT_SECONDS):
                result = (
                    await self.client.catalog(token, version)
                    if endpoint == "catalog"
                    else await self.client.usage(token, version)
                )
        except (ClaudeError, TimeoutError) as exc:
            error = str(exc) if isinstance(exc, ClaudeError) else f"Claude {endpoint} metadata timed out"
            retry_at = exc.retry_at if isinstance(exc, MetadataHTTPError) else datetime.now(UTC) + USAGE_INTERVAL
        completed_at = datetime.now(UTC)

        def finish(state: AccountState) -> AccountState | None:
            refresh = state.metadata_refresh.get(endpoint)
            if (
                refresh is None
                or refresh.operation_id != operation_id
                or refresh.lease_until is None
                or refresh.lease_until <= completed_at
            ):
                return None
            state.metadata_refresh[endpoint] = MetadataRefreshState(retry_at=retry_at)
            if endpoint == "catalog":
                state.catalog_requested_at = requested_at
                state.catalog_error = error
                if error is None:
                    assert isinstance(result, list)
                    state.catalog = result
                    state.catalog_updated_at = completed_at
            else:
                state.usage_check_started_at = requested_at
                state.usage_error = error
                if error is None:
                    assert isinstance(result, UsageSnapshot)
                    state.usage = result
                    state.usage_requested_at = requested_at
                    state.usage_updated_at = completed_at
            return state

        merged = await self.repository.mutate_state(source_id, generation, finish)
        if merged is not None and error is None:
            if endpoint == "catalog":
                row = await self._get(source_id)
                await self.repository.sources.replace_models(row.source, project_models(merged), commit=False)
            else:
                effective = quota_status(merged, now=completed_at)
                sample = UsageSnapshot.model_validate(
                    {
                        window.name: {"utilization": window.utilization, "resets_at": window.resets_at}
                        for window in effective.windows
                        if window.provenance == "usage_api"
                        and window.observed_at == completed_at
                        and window.freshness == "fresh"
                    }
                )
                await self.repository.record_quota(source_id, sample, completed_at, sample_seconds=60)
        await self.repository.session.commit()

    async def _save(self, row: ClaudeAccount, state: AccountState, *, project: bool) -> None:
        baseline = AccountState.model_validate_json(row.state_json).model_dump()
        changes = {key: value for key, value in state.model_dump().items() if value != baseline[key]}

        def merge(current: AccountState) -> AccountState:
            return AccountState.model_validate({**current.model_dump(), **changes})

        try:
            await self.repository.session.flush()
            merged = await self.repository.mutate_state(row.source_id, row.generation, merge)
            if merged is None:
                raise ClaudeError("Claude credentials changed during update; reload and retry")
            if project:
                await self.repository.sources.replace_models(row.source, project_models(merged), commit=False)
            await self.repository.session.commit()
            await self.repository.session.refresh(row)
        except StaleDataError as exc:
            await self.repository.session.rollback()
            raise ClaudeError("Claude account changed during refresh; reload and retry") from exc

    async def delete(self, source_id: str) -> None:
        await self._get(source_id)
        await self.repository.sources.delete(source_id)

    @staticmethod
    def _response(row: ClaudeAccount) -> ClaudeAccountResponse:
        status = row.credential_status
        if status == "ready" and row.identity_fingerprint is None:
            status = "unverified"
        state = AccountState.model_validate_json(row.state_json)
        if row.refresh_intent and row.refresh_started_at and row.refresh_started_at < utcnow() - timedelta(minutes=1):
            status = "uncertain"
        return ClaudeAccountResponse(
            routing_policy=AccountRoutingPolicy(row.routing_policy),
            max_concurrency=row.source.max_concurrency,
            id=row.source_id,
            name=row.source.name,
            is_enabled=row.source.is_enabled,
            credential_status=status,
            expires_at=row.expires_at.replace(tzinfo=UTC),
            state=state,
            quota=quota_status(state, now=datetime.now(UTC)),
        )


def project_models(state: AccountState) -> list[ModelSourceModel]:
    from app.core.usage.pricing import get_pricing_for_model

    catalog = {model.id: model for model in state.catalog}
    result: list[ModelSourceModel] = []
    for selection in state.selections:
        model = catalog.get(selection.model)
        limits = model.token_limits if model else None
        policy = model_policy(selection.model)
        resolved_price = get_pricing_for_model(selection.model)
        price = resolved_price[1] if resolved_price is not None else None
        result.append(
            ModelSourceModel(
                model=f"anthropic/{selection.model}",
                display_name=model.display_name if model else selection.model,
                context_window=limits.context_window if limits else None,
                max_output_tokens=limits.max_output_tokens if limits else None,
                is_enabled=limits is not None,
                supports_streaming=True,
                supports_tools=True,
                supports_vision=True,
                input_per_1m=price.input_per_1m if price is not None else None,
                cached_input_per_1m=price.cached_input_per_1m if price is not None else None,
                output_per_1m=price.output_per_1m if price is not None else None,
                raw_metadata_json=json.dumps(
                    {
                        **(
                            {
                                "auto_compact_token_limit": limits.context_window * 9 // 10,
                                "effective_context_window_percent": 95,
                            }
                            if limits
                            else {}
                        ),
                        "upstream_model": selection.model,
                        "supports_reasoning": bool(policy and policy.supports_reasoning),
                        "supported_reasoning_levels": ["low", "medium", "high", "max"]
                        if policy and policy.supports_reasoning
                        else [],
                        "default_reasoning_level": "medium" if policy and policy.supports_reasoning else None,
                    }
                ),
            )
        )
    return result
