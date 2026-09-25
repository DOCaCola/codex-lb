from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelSourceModel, OpenRouterAccount
from app.modules.model_sources.repository import ModelSourcesRepository


class OpenRouterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = ModelSourcesRepository(session)

    async def list_accounts(self) -> list[OpenRouterAccount]:
        rows = await self.session.scalars(select(OpenRouterAccount))
        return sorted(rows.unique(), key=lambda row: (row.source.name, row.source_id))

    async def get(self, source_id: str) -> OpenRouterAccount | None:
        return await self.session.get(OpenRouterAccount, source_id)

    async def add(self, row: OpenRouterAccount) -> None:
        self.session.add(row)
        await self.session.flush()

    async def save(self, row: OpenRouterAccount, state_json: str, models: list[ModelSourceModel] | None) -> None:
        row.state_json = state_json
        # Optimistic version check precedes routing projection replacement.
        await self.session.flush()
        if models is not None:
            await self.sources.replace_models(row.source, models, commit=False)
        await self.session.commit()
        if models is not None:
            await self.sources.refresh_models(row.source)

    async def rollback(self) -> None:
        await self.session.rollback()

    async def delete(self, source_id: str) -> None:
        await self.sources.delete(source_id)
