from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelSourceModel, OpenAIApiAccount, RequestLog
from app.modules.model_sources.repository import ModelSourcesRepository


class OpenAIApiRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = ModelSourcesRepository(session)

    async def list_accounts(self) -> list[OpenAIApiAccount]:
        rows = await self.session.scalars(select(OpenAIApiAccount))
        return sorted(rows.unique(), key=lambda row: (row.source.name, row.source_id))

    async def get(self, source_id: str) -> OpenAIApiAccount | None:
        return await self.session.get(OpenAIApiAccount, source_id)

    async def add(self, row: OpenAIApiAccount) -> None:
        self.session.add(row)
        await self.session.flush()

    async def save(self, row: OpenAIApiAccount, state_json: str, models: list[ModelSourceModel] | None) -> None:
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

    async def spent_since(self, source_id: str, since: datetime) -> float:
        """Cost recorded on the account; log retention does not change what the credit already paid for."""
        total = await self.session.scalar(
            select(func.coalesce(func.sum(RequestLog.cost_usd), 0.0)).where(
                RequestLog.model_source_id == source_id, RequestLog.requested_at >= since
            )
        )
        return float(total or 0.0)
