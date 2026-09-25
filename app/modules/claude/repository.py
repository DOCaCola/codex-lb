from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClaudeAccount, ClaudeOAuthFlow
from app.modules.model_sources.repository import ModelSourcesRepository


class ClaudeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = ModelSourcesRepository(session)

    async def get(self, source_id: str) -> ClaudeAccount | None:
        return await self.session.get(ClaudeAccount, source_id, populate_existing=True)

    async def list_accounts(self) -> list[ClaudeAccount]:
        return list((await self.session.scalars(select(ClaudeAccount))).unique())

    async def consume_flow(self, state_hash: str, now: datetime) -> ClaudeOAuthFlow | None:
        row = await self.session.scalar(
            delete(ClaudeOAuthFlow)
            .where(ClaudeOAuthFlow.state_hash == state_hash, ClaudeOAuthFlow.expires_at > now)
            .returning(ClaudeOAuthFlow)
        )
        await self.session.commit()
        return row

    async def claim_refresh(self, source_id: str, generation: int, intent: str, now: datetime) -> bool:
        claimed = await self.session.scalar(
            update(ClaudeAccount)
            .where(
                ClaudeAccount.source_id == source_id,
                ClaudeAccount.generation == generation,
                ClaudeAccount.credential_status == "ready",
                ClaudeAccount.refresh_intent.is_(None),
                or_(ClaudeAccount.retry_at.is_(None), ClaudeAccount.retry_at <= now),
            )
            .values(refresh_intent=intent, refresh_started_at=now, version=ClaudeAccount.version + 1)
            .returning(ClaudeAccount.source_id)
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return claimed is not None

    async def finish_refresh(
        self,
        source_id: str,
        generation: int,
        intent: str,
        *,
        status: str,
        retry_at: datetime | None = None,
        encrypted: bytes | None = None,
        expires_at: datetime | None = None,
        fingerprint: str | None = None,
    ) -> bool:
        statement = update(ClaudeAccount).where(
            ClaudeAccount.source_id == source_id,
            ClaudeAccount.generation == generation,
            ClaudeAccount.refresh_intent == intent,
        )
        statement = statement.values(
            credential_status=status,
            refresh_intent=intent if status == "uncertain" else None,
            refresh_started_at=ClaudeAccount.refresh_started_at if status == "uncertain" else None,
            retry_at=retry_at,
            version=ClaudeAccount.version + 1,
        )
        if encrypted is not None:
            statement = statement.values(
                credentials_encrypted=encrypted,
                expires_at=expires_at,
                grant_fingerprint=fingerprint,
                generation=generation + 1,
            )
        result = await self.session.scalar(
            statement.returning(ClaudeAccount.source_id).execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return result is not None
