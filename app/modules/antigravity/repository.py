from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage.recent import Reading, RecentLookbacks
from app.core.utils.time import utcnow
from app.db.models import AntigravityAccount, AntigravityCooldown, AntigravityOAuthFlow, AntigravityQuotaHistory
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.quota import WINDOW_LENGTHS
from app.modules.antigravity.schemas import AccountState, QuotaBucket, QuotaFamily, QuotaWindowName
from app.modules.model_sources.repository import ModelSourcesRepository

QUOTA_HISTORY_RETENTION = timedelta(days=30)
# An unchanged reading within this interval adds no evidence to the history.
QUOTA_SAMPLE_INTERVAL = timedelta(minutes=10)


def _naive(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


class AntigravityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = ModelSourcesRepository(session)

    async def get(self, source_id: str) -> AntigravityAccount | None:
        return await self.session.get(AntigravityAccount, source_id, populate_existing=True)

    async def by_subject(self, subject: str) -> AntigravityAccount | None:
        return await self.session.scalar(select(AntigravityAccount).where(AntigravityAccount.google_subject == subject))

    async def list_accounts(self) -> list[AntigravityAccount]:
        rows = await self.session.scalars(select(AntigravityAccount))
        return sorted(rows.unique(), key=lambda row: (row.source.name, row.source_id))

    async def recent_quota_baselines(
        self, source_ids: Sequence[str], now: datetime, lookbacks: RecentLookbacks
    ) -> dict[str, dict[tuple[QuotaFamily, QuotaWindowName], Reading]]:
        """Each account's newest reading per family window at the start of its recent-usage lookback (naive UTC)."""
        baselines: dict[str, dict[tuple[QuotaFamily, QuotaWindowName], Reading]] = {}
        for lookback, names in lookbacks.group(WINDOW_LENGTHS).items():
            cutoff = now - lookback
            ranked = (
                select(
                    AntigravityQuotaHistory.source_id,
                    AntigravityQuotaHistory.family,
                    AntigravityQuotaHistory.window,
                    AntigravityQuotaHistory.observed_at,
                    AntigravityQuotaHistory.used_percent,
                    func.row_number()
                    .over(
                        partition_by=(
                            AntigravityQuotaHistory.source_id,
                            AntigravityQuotaHistory.family,
                            AntigravityQuotaHistory.window,
                        ),
                        order_by=AntigravityQuotaHistory.observed_at.desc(),
                    )
                    .label("rank"),
                )
                .where(
                    AntigravityQuotaHistory.source_id.in_(source_ids),
                    AntigravityQuotaHistory.window.in_(names),
                    AntigravityQuotaHistory.observed_at <= cutoff,
                    # An older reading predates every current window of these lengths.
                    AntigravityQuotaHistory.observed_at >= cutoff - max(WINDOW_LENGTHS[name] for name in names),
                )
                .subquery()
            )
            for row in await self.session.execute(select(ranked).where(ranked.c.rank == 1)):
                baselines.setdefault(row.source_id, {})[(row.family, row.window)] = Reading(
                    row.observed_at, row.used_percent
                )
        return baselines

    async def mutate_state(
        self, source_id: str, generation: int, mutate: Callable[[AccountState], AccountState | None]
    ) -> AccountState | None:
        """Merge against current state; the caller owns the commit."""
        for _ in range(3):
            row = (
                await self.session.execute(
                    select(AntigravityAccount.state_json, AntigravityAccount.version).where(
                        AntigravityAccount.source_id == source_id, AntigravityAccount.generation == generation
                    )
                )
            ).one_or_none()
            if row is None:
                return None
            state = mutate(AccountState.model_validate_json(row.state_json))
            if state is None:
                return None
            changed = await self.session.scalar(
                update(AntigravityAccount)
                .where(
                    AntigravityAccount.source_id == source_id,
                    AntigravityAccount.generation == generation,
                    AntigravityAccount.version == row.version,
                )
                .values(state_json=state.model_dump_json(), version=AntigravityAccount.version + 1)
                .returning(AntigravityAccount.source_id)
                .execution_options(synchronize_session=False)
            )
            if changed is not None:
                return state
        raise AntigravityError("Antigravity account changed concurrently; retry the update")

    async def update_account(self, source_id: str, generation: int, /, **values: object) -> bool:
        """Compare-and-set on the credential generation; values may advance the generation itself."""
        changed = await self.session.scalar(
            update(AntigravityAccount)
            .where(AntigravityAccount.source_id == source_id, AntigravityAccount.generation == generation)
            .values(**values, version=AntigravityAccount.version + 1)
            .returning(AntigravityAccount.source_id)
            .execution_options(synchronize_session=False)
        )
        return changed is not None

    async def record_quota(self, source_id: str, buckets: Sequence[QuotaBucket], observed_at: datetime) -> None:
        observed = _naive(observed_at)
        for bucket in buckets:
            reset = _naive(bucket.resets_at) if bucket.resets_at else None
            last = await self.session.scalar(
                select(AntigravityQuotaHistory)
                .where(
                    AntigravityQuotaHistory.source_id == source_id,
                    AntigravityQuotaHistory.family == bucket.family,
                    AntigravityQuotaHistory.window == bucket.window,
                )
                .order_by(AntigravityQuotaHistory.observed_at.desc())
                .limit(1)
            )
            if (
                last is not None
                and observed - last.observed_at < QUOTA_SAMPLE_INTERVAL
                and last.used_percent == bucket.used_percent
                and last.resets_at == reset
            ):
                continue
            self.session.add(
                AntigravityQuotaHistory(
                    source_id=source_id,
                    observed_at=observed,
                    family=bucket.family,
                    window=bucket.window,
                    used_percent=bucket.used_percent,
                    resets_at=reset,
                )
            )
        await self.session.execute(
            delete(AntigravityQuotaHistory).where(
                AntigravityQuotaHistory.source_id == source_id,
                AntigravityQuotaHistory.observed_at < observed - QUOTA_HISTORY_RETENTION,
            )
        )

    async def consume_flow(self, state_hash: str) -> AntigravityOAuthFlow | None:
        row = await self.session.scalar(
            delete(AntigravityOAuthFlow)
            .where(AntigravityOAuthFlow.state_hash == state_hash, AntigravityOAuthFlow.expires_at > utcnow())
            .returning(AntigravityOAuthFlow)
        )
        await self.session.commit()
        return row

    async def cooldowns(self, source_ids: Sequence[str], now: datetime) -> list[AntigravityCooldown]:
        if not source_ids:
            return []
        rows = await self.session.scalars(
            select(AntigravityCooldown).where(
                AntigravityCooldown.source_id.in_(list(source_ids)), AntigravityCooldown.until > _naive(now)
            )
        )
        return list(rows)

    async def cool_down(self, source_id: str, scope: str, until: datetime, reason: str) -> None:
        """Extend, never shorten, a cooldown; the caller owns the commit."""
        until = _naive(until)
        existing = await self.session.get(AntigravityCooldown, (source_id, scope), populate_existing=True)
        if existing is None:
            self.session.add(AntigravityCooldown(source_id=source_id, scope=scope, until=until, reason=reason))
        elif existing.until < until:
            existing.until = until
            existing.reason = reason
        await self.session.flush()

    async def clear_cooldowns(self, source_id: str) -> None:
        await self.session.execute(delete(AntigravityCooldown).where(AntigravityCooldown.source_id == source_id))
