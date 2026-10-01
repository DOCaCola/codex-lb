from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClaudeAccount, ClaudeOAuthFlow, ClaudeQuotaHistory
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.schemas import AccountState, UsageSnapshot
from app.modules.model_sources.repository import ModelSourcesRepository


class ClaudeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = ModelSourcesRepository(session)

    async def get(self, source_id: str) -> ClaudeAccount | None:
        return await self.session.get(ClaudeAccount, source_id, populate_existing=True)

    async def list_accounts(self) -> list[ClaudeAccount]:
        rows = await self.session.scalars(select(ClaudeAccount))
        return sorted(rows.unique(), key=lambda row: (row.source.name, row.source_id))

    async def mutate_state(
        self, source_id: str, generation: int, mutate: Callable[[AccountState], AccountState | None]
    ) -> AccountState | None:
        """Merge against current state; caller owns commit and related history/settings writes."""
        for _ in range(3):
            row = (
                await self.session.execute(
                    select(ClaudeAccount.state_json, ClaudeAccount.version).where(
                        ClaudeAccount.source_id == source_id, ClaudeAccount.generation == generation
                    )
                )
            ).one_or_none()
            if row is None:
                return None
            state = mutate(AccountState.model_validate_json(row.state_json))
            if state is None:
                return None
            changed = await self.session.scalar(
                update(ClaudeAccount)
                .where(
                    ClaudeAccount.source_id == source_id,
                    ClaudeAccount.generation == generation,
                    ClaudeAccount.version == row.version,
                )
                .values(state_json=state.model_dump_json(), version=ClaudeAccount.version + 1)
                .returning(ClaudeAccount.source_id)
                .execution_options(synchronize_session=False)
            )
            if changed is not None:
                return state
        raise ClaudeError("Claude account changed concurrently; retry the update")

    async def record_quota(
        self, source_id: str, usage: UsageSnapshot, observed_at: datetime, *, sample_seconds: int = 0
    ) -> None:
        observed_at = observed_at.astimezone(UTC).replace(tzinfo=None)
        for name, window in (
            ("five_hour", usage.five_hour),
            ("seven_day", usage.seven_day),
            ("seven_day_opus", usage.seven_day_opus),
            ("seven_day_sonnet", usage.seven_day_sonnet),
        ):
            if window is not None:
                reset = window.resets_at.astimezone(UTC).replace(tzinfo=None) if window.resets_at else None
                if sample_seconds:
                    # Only an unchanged reading is redundant: a value that moved
                    # within the interval (e.g. 99% to 100%) is new evidence.
                    last = await self.session.scalar(
                        select(ClaudeQuotaHistory)
                        .where(ClaudeQuotaHistory.source_id == source_id, ClaudeQuotaHistory.window == name)
                        .order_by(ClaudeQuotaHistory.observed_at.desc())
                        .limit(1)
                    )
                    if (
                        last is not None
                        and observed_at - last.observed_at < timedelta(seconds=sample_seconds)
                        and last.used_percent == window.utilization
                    ):
                        previous_reset = (
                            round(last.resets_at.replace(tzinfo=UTC).timestamp()) if last.resets_at else None
                        )
                        current_reset = round(reset.replace(tzinfo=UTC).timestamp()) if reset else None
                        if previous_reset == current_reset:
                            continue
                self.session.add(
                    ClaudeQuotaHistory(
                        source_id=source_id,
                        observed_at=observed_at,
                        window=name,
                        used_percent=window.utilization,
                        resets_at=reset,
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
