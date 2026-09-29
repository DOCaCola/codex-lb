from __future__ import annotations

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
from app.modules.claude.quota import quota_status
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import (
    CLAUDE_BASE_URL,
    CLAUDE_KIND,
    AccountState,
    ClaudeAccountResponse,
    ClaudeImport,
    ClaudeReconnect,
    ClaudeUpdate,
    Credentials,
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

    async def refresh(self, source_id: str, *, catalog: bool = True) -> ClaudeAccountResponse:
        snapshot = await self.auth.snapshot(source_id)
        credentials = snapshot.credentials
        row = await self._get(source_id)
        if row.generation != snapshot.generation:
            raise ClaudeError("Claude credentials changed before metadata refresh")
        state = AccountState.model_validate_json(row.state_json)
        identity = await ClaudeVersionService(self.repository.session).snapshot()
        token = credentials.access_token.get_secret_value()
        changed = False
        if catalog:
            state.catalog_requested_at = datetime.now(UTC)
            try:
                state.catalog = await self.client.catalog(token, identity.version)
                state.catalog_updated_at = datetime.now(UTC)
                state.catalog_error = None
                changed = True
            except ClaudeError as exc:
                state.catalog_error = str(exc)
        requested_at = datetime.now(UTC)
        state.usage_check_started_at = requested_at
        try:
            state.usage = await self.client.usage(token, identity.version)
            state.usage_updated_at = datetime.now(UTC)
            state.usage_requested_at = requested_at
            state.usage_error = None
        except ClaudeError as exc:
            state.usage_error = str(exc)
        await self._save(row, state, project=changed)
        return self._response(row)

    async def _save(self, row: ClaudeAccount, state: AccountState, *, project: bool) -> None:
        baseline = AccountState.model_validate_json(row.state_json).model_dump()
        changes = {key: value for key, value in state.model_dump().items() if value != baseline[key]}
        poll_fields = ("usage", "usage_updated_at", "usage_requested_at", "usage_error", "usage_check_started_at")
        catalog_fields = ("catalog", "catalog_updated_at", "catalog_error", "catalog_requested_at")
        desired = state.model_dump()
        for marker, fields in (("usage_check_started_at", poll_fields), ("catalog_requested_at", catalog_fields)):
            if marker in changes:
                changes.update({key: desired[key] for key in fields})

        def merge(current: AccountState) -> AccountState:
            updates = dict(changes)
            if (
                current.usage_check_started_at is not None
                and state.usage_check_started_at is not None
                and current.usage_check_started_at > state.usage_check_started_at
            ):
                for key in poll_fields:
                    updates.pop(key, None)
            if (
                current.catalog_requested_at is not None
                and state.catalog_requested_at is not None
                and current.catalog_requested_at > state.catalog_requested_at
            ):
                for key in catalog_fields:
                    updates.pop(key, None)
            return AccountState.model_validate({**current.model_dump(), **updates})

        try:
            await self.repository.session.flush()
            merged = await self.repository.mutate_state(row.source_id, row.generation, merge)
            if merged is None:
                raise ClaudeError("Claude credentials changed during update; reload and retry")
            if project:
                await self.repository.sources.replace_models(row.source, project_models(merged), commit=False)
            if "usage" in changes and merged.usage is not None and merged.usage_updated_at is not None:
                effective = quota_status(merged, now=datetime.now(UTC))
                sample = UsageSnapshot.model_validate(
                    {
                        window.name: {"utilization": window.utilization, "resets_at": window.resets_at}
                        for window in effective.windows
                        if window.provenance == "usage_api"
                        and window.observed_at == state.usage_updated_at
                        and window.freshness == "fresh"
                    }
                )
                await self.repository.record_quota(row.source_id, sample, merged.usage_updated_at, sample_seconds=60)
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
    catalog = {model.id: model for model in state.catalog}
    result: list[ModelSourceModel] = []
    for selection in state.selections:
        model = catalog.get(selection.model)
        limits = model.token_limits if model else None
        policy = model_policy(selection.model)
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
                        "supports_reasoning": bool(policy and policy.adaptive_reasoning),
                        "supported_reasoning_levels": ["low", "medium", "high", "max"]
                        if policy and policy.adaptive_reasoning
                        else [],
                        "default_reasoning_level": "medium" if policy and policy.adaptive_reasoning else None,
                    }
                ),
            )
        )
    return result
