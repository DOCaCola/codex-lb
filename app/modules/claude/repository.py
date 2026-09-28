from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClaudeAccount, ClaudeOAuthFlow, ClaudeQuotaHistory
from app.modules.claude.schemas import UsageSnapshot
from app.modules.model_sources.repository import ModelSourcesRepository


class ClaudeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = ModelSourcesRepository(session)

    async def get(self, source_id: str) -> ClaudeAccount | None:
        return await self.session.get(ClaudeAccount, source_id, populate_existing=True)

    async def list_accounts(self) -> list[ClaudeAccount]:
        return list((await self.session.scalars(select(ClaudeAccount))).unique())

    async def record_quota(self, source_id: str, usage: UsageSnapshot, observed_at: datetime) -> None:
        observed_at = observed_at.astimezone(UTC).replace(tzinfo=None)
        for name, window in (
            ("five_hour", usage.five_hour),
            ("seven_day", usage.seven_day),
            ("seven_day_opus", usage.seven_day_opus),
            ("seven_day_sonnet", usage.seven_day_sonnet),
        ):
            if window is not None:
                self.session.add(
                    ClaudeQuotaHistory(
                        source_id=source_id, observed_at=observed_at, window=name, used_percent=window.utilization
                    )
                )
        await self.session.execute(
            delete(ClaudeQuotaHistory).where(
                ClaudeQuotaHistory.source_id == source_id,
                ClaudeQuotaHistory.observed_at < observed_at - timedelta(days=30),
            )
        )

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

    async def backoff_rejected_generation(self, source_id: str, generation: int, now: datetime) -> None:
        from sqlalchemy import case

        until = now + timedelta(minutes=10)
        await self.session.execute(
            update(ClaudeAccount)
            .where(
                ClaudeAccount.source_id == source_id,
                ClaudeAccount.generation == generation,
                ClaudeAccount.credential_status == "ready",
                ClaudeAccount.refresh_intent.is_(None),
            )
            .values(
                retry_at=case((ClaudeAccount.retry_at > until, ClaudeAccount.retry_at), else_=until),
                version=ClaudeAccount.version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()

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
