from __future__ import annotations

import uuid

from sqlalchemy.orm.exc import StaleDataError

from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import ModelSource, OpenRouterAccount
from app.modules.model_sources.service import ModelSourceNotFoundError
from app.modules.openrouter.catalog import project_models
from app.modules.openrouter.client import OpenRouterClient, OpenRouterError
from app.modules.openrouter.repository import OpenRouterRepository
from app.modules.openrouter.schemas import (
    OPENROUTER_BASE_URL,
    OPENROUTER_KIND,
    AccountState,
    OpenRouterAccountResponse,
    OpenRouterCreate,
    OpenRouterUpdate,
)


class OpenRouterService:
    def __init__(self, repository: OpenRouterRepository, client: OpenRouterClient | None = None) -> None:
        self.repository = repository
        self.client = client or OpenRouterClient()
        self.encryptor = TokenEncryptor()

    async def list_accounts(self) -> list[OpenRouterAccountResponse]:
        return [self._response(row) for row in await self.repository.list_accounts()]

    async def _get(self, source_id: str) -> OpenRouterAccount:
        row = await self.repository.get(source_id)
        if row is None:
            raise ModelSourceNotFoundError("OpenRouter account not found")
        return row

    async def create(self, payload: OpenRouterCreate) -> OpenRouterAccountResponse:
        key = payload.api_key.get_secret_value().strip()
        info = await self.client.key_info(key)
        if info.is_management_key:
            raise OpenRouterError("Use an inference key for requests; a management key cannot run models")
        name = payload.name.strip()
        if not name:
            raise OpenRouterError("Account name is required")
        source = ModelSource(
            id=f"src_{uuid.uuid4().hex}",
            name=name,
            kind=OPENROUTER_KIND,
            base_url=OPENROUTER_BASE_URL,
            api_key_encrypted=self.encryptor.encrypt(key),
            is_enabled=True,
            health_status="unknown",
            supports_chat_completions=True,
            supports_responses=True,
            supports_audio_transcriptions=False,
            supports_embeddings=False,
            models=[],
        )
        state = AccountState(key=info, key_updated_at=utcnow())
        row = OpenRouterAccount(
            source_id=source.id,
            source=source,
            management_key_encrypted=(
                self.encryptor.encrypt(payload.management_key.get_secret_value()) if payload.management_key else None
            ),
            state_json=state.model_dump_json(exclude_unset=True),
        )
        await self.repository.add(row)
        return await self.refresh(row.source_id, catalog=True)

    async def update(self, source_id: str, payload: OpenRouterUpdate) -> OpenRouterAccountResponse:
        row = await self._get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        if payload.name is not None:
            if not payload.name.strip():
                raise OpenRouterError("Account name is required")
            row.source.name = payload.name.strip()
        if payload.is_enabled is not None:
            row.source.is_enabled = payload.is_enabled
        if payload.api_key is not None:
            key = payload.api_key.get_secret_value().strip()
            info = await self.client.key_info(key)
            if info.is_management_key:
                raise OpenRouterError("An inference key is required")
            row.source.api_key_encrypted = self.encryptor.encrypt(key)
            state.key = info
            state.key_updated_at = utcnow()
            state.key_error = None
            # Changed identity requires fresh availability before routing.
            state.catalog = (await self.client.catalog(key)).data
            state.catalog_updated_at = utcnow()
            state.catalog_error = None
        if "management_key" in payload.model_fields_set:
            row.management_key_encrypted = (
                self.encryptor.encrypt(payload.management_key.get_secret_value()) if payload.management_key else None
            )
            state.credits = None
            state.credits_updated_at = None
            state.credits_error = None
        if payload.selections is not None:
            ids = [item.model for item in payload.selections]
            if len(ids) != len(set(ids)):
                raise OpenRouterError("Models must be selected only once")
            known = {item.id for item in state.catalog} | {item.model for item in state.selections}
            if set(ids) - known:
                raise OpenRouterError("Select models from the synchronized account catalog")
            state.selections = payload.selections
        await self._save(row, state, project=True)
        return self._response(row)

    async def refresh(self, source_id: str, *, catalog: bool = True) -> OpenRouterAccountResponse:
        row = await self._get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        assert row.source.api_key_encrypted is not None
        key = self.encryptor.decrypt(row.source.api_key_encrypted)
        try:
            state.key = await self.client.key_info(key)
            state.key_updated_at = utcnow()
            state.key_error = None
        except OpenRouterError as exc:
            state.key_error = str(exc)
        catalog_changed = False
        if catalog:
            try:
                result = await self.client.catalog(key)
                state.catalog = [model for model in result.data if "text" in model.architecture.output_modalities]
                state.catalog_updated_at = utcnow()
                state.catalog_error = None
                catalog_changed = True
            except OpenRouterError as exc:
                state.catalog_error = str(exc)
        if row.management_key_encrypted is not None:
            try:
                state.credits = await self.client.credits(self.encryptor.decrypt(row.management_key_encrypted))
                state.credits_updated_at = utcnow()
                state.credits_error = None
            except OpenRouterError as exc:
                state.credits_error = str(exc)
        await self._save(row, state, project=catalog_changed)
        return self._response(row)

    async def _save(self, row: OpenRouterAccount, state: AccountState, *, project: bool) -> None:
        try:
            await self.repository.save(
                row, state.model_dump_json(exclude_unset=True), project_models(state) if project else None
            )
        except StaleDataError as exc:
            await self.repository.rollback()
            raise OpenRouterError("Account changed during refresh; reload and retry") from exc

    async def delete(self, source_id: str) -> None:
        await self._get(source_id)
        await self.repository.delete(source_id)

    @staticmethod
    def _response(row: OpenRouterAccount) -> OpenRouterAccountResponse:
        return OpenRouterAccountResponse(
            id=row.source_id,
            name=row.source.name,
            is_enabled=row.source.is_enabled,
            has_management_key=row.management_key_encrypted is not None,
            state=AccountState.model_validate_json(row.state_json),
        )
