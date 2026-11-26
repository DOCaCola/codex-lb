from __future__ import annotations

import uuid

from sqlalchemy.orm.exc import StaleDataError

from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import AccountRoutingPolicy, ModelSource, OpenAIApiAccount
from app.modules.model_sources.pooled_accounts import clear_cooldowns, cooldown_until
from app.modules.model_sources.service import ModelSourceNotFoundError
from app.modules.openai_api.catalog import catalog_models, project_models
from app.modules.openai_api.client import OpenAIApiClient, OpenAIApiError
from app.modules.openai_api.credit import credit_cycle
from app.modules.openai_api.repository import OpenAIApiRepository
from app.modules.openai_api.schemas import (
    OPENAI_API_BASE_URL,
    OPENAI_API_KIND,
    AccountState,
    CreditEstimate,
    OpenAIApiAccountResponse,
    OpenAIApiCreate,
    OpenAIApiUpdate,
)


class OpenAIApiService:
    def __init__(self, repository: OpenAIApiRepository, client: OpenAIApiClient | None = None) -> None:
        self.repository = repository
        self.client = client or OpenAIApiClient()
        self.encryptor = TokenEncryptor()

    async def list_accounts(self) -> list[OpenAIApiAccountResponse]:
        return [await self._response(row) for row in await self.repository.list_accounts()]

    async def get(self, source_id: str) -> OpenAIApiAccount:
        row = await self.repository.get(source_id)
        if row is None:
            raise ModelSourceNotFoundError("OpenAI API account not found")
        return row

    async def create(self, payload: OpenAIApiCreate) -> OpenAIApiAccountResponse:
        name = payload.name.strip()
        if not name:
            raise OpenAIApiError("Account name is required")
        key = payload.api_key.get_secret_value().strip()
        catalog = catalog_models(await self.client.models(key))
        source = ModelSource(
            id=f"src_{uuid.uuid4().hex}",
            name=name,
            kind=OPENAI_API_KIND,
            base_url=OPENAI_API_BASE_URL,
            api_key_encrypted=self.encryptor.encrypt(key),
            is_enabled=True,
            health_status="unknown",
            supports_chat_completions=True,
            supports_responses=True,
            supports_audio_transcriptions=False,
            supports_embeddings=False,
            models=[],
        )
        state = AccountState(
            catalog=catalog,
            catalog_updated_at=utcnow(),
            monthly_credit_usd=payload.monthly_credit_usd,
            credit_renews_on=payload.credit_renews_on,
        )
        row = OpenAIApiAccount(source_id=source.id, source=source, state_json=state.model_dump_json())
        await self.repository.add(row)
        await self._save(row, state, project=True)
        return await self._response(row)

    async def update(self, source_id: str, payload: OpenAIApiUpdate) -> OpenAIApiAccountResponse:
        row = await self.get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        if payload.name is not None:
            if not payload.name.strip():
                raise OpenAIApiError("Account name is required")
            row.source.name = payload.name.strip()
        if payload.is_enabled is not None:
            row.source.is_enabled = payload.is_enabled
        if payload.routing_policy is not None:
            row.routing_policy = payload.routing_policy.value
        if "monthly_credit_usd" in payload.model_fields_set:
            state.monthly_credit_usd = payload.monthly_credit_usd
        if "credit_renews_on" in payload.model_fields_set:
            state.credit_renews_on = payload.credit_renews_on
        project = False
        if payload.api_key is not None:
            key = payload.api_key.get_secret_value().strip()
            # A changed identity needs its own availability before it routes.
            state.catalog = catalog_models(await self.client.models(key))
            state.catalog_updated_at = utcnow()
            state.catalog_error = None
            row.source.api_key_encrypted = self.encryptor.encrypt(key)
            await clear_cooldowns(self.repository.session, source_id)
            project = True
        if payload.selections is not None:
            ids = [item.model for item in payload.selections]
            if len(ids) != len(set(ids)):
                raise OpenAIApiError("Models must be selected only once")
            known = {item.id for item in state.catalog} | {item.model for item in state.selections}
            if set(ids) - known:
                raise OpenAIApiError("Select models from the synchronized account catalog")
            state.selections = payload.selections
            project = True
        await self._save(row, state, project=project)
        return await self._response(row)

    async def refresh(self, source_id: str, *, operator: bool) -> OpenAIApiAccountResponse:
        row = await self.get(source_id)
        state = AccountState.model_validate_json(row.state_json)
        assert row.source.api_key_encrypted is not None
        changed = False
        try:
            state.catalog = catalog_models(
                await self.client.models(self.encryptor.decrypt(row.source.api_key_encrypted))
            )
            state.catalog_updated_at = utcnow()
            state.catalog_error = None
            changed = True
        except OpenAIApiError as exc:
            state.catalog_error = str(exc)
        if operator:
            # The operator's refresh is the signal that credit was added or limits were raised.
            await clear_cooldowns(self.repository.session, source_id)
        await self._save(row, state, project=changed)
        return await self._response(row)

    async def delete(self, source_id: str) -> None:
        await self.get(source_id)
        await self.repository.delete(source_id)

    async def _save(self, row: OpenAIApiAccount, state: AccountState, *, project: bool) -> None:
        try:
            await self.repository.save(row, state.model_dump_json(), project_models(state) if project else None)
        except StaleDataError as exc:
            await self.repository.rollback()
            raise OpenAIApiError("Account changed during refresh; reload and retry") from exc

    async def _response(self, row: OpenAIApiAccount) -> OpenAIApiAccountResponse:
        state = AccountState.model_validate_json(row.state_json)
        now = utcnow()
        # Without a configured renewal day the estimate follows the calendar month.
        cycle_start, cycle_end = credit_cycle(state.credit_renews_on or 1, now)
        spent = await self.repository.spent_since(row.source_id, cycle_start)
        return OpenAIApiAccountResponse(
            routing_policy=AccountRoutingPolicy(row.routing_policy),
            id=row.source_id,
            name=row.source.name,
            is_enabled=row.source.is_enabled,
            state=state,
            credit=CreditEstimate(
                cycle_start=cycle_start,
                cycle_end=cycle_end,
                spent_usd=spent,
                monthly_credit_usd=state.monthly_credit_usd,
                remaining_usd=(
                    max(0.0, state.monthly_credit_usd - spent) if state.monthly_credit_usd is not None else None
                ),
                exhausted_until=await cooldown_until(self.repository.session, row.source_id),
            ),
        )
