"""Operator-set subscription end dates on provider accounts.

Neither provider reports a cancellation date, so the end is entered by hand. It
applies to accounts with a renewing quota window: Codex accounts and Claude and
Antigravity model sources. Projections treat it as a capacity cutoff; routing
does not read it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.time import to_utc_naive
from app.db.models import Account, ModelSource
from app.db.session import sqlite_writer_section
from app.modules.antigravity.constants import ANTIGRAVITY_KIND
from app.modules.claude.schemas import CLAUDE_KIND

SUBSCRIPTION_SOURCE_KINDS = frozenset((CLAUDE_KIND, ANTIGRAVITY_KIND))

SourceUpdateResult = Literal["updated", "not_found", "not_applicable"]


@dataclass(frozen=True, slots=True)
class AccountSubscriptionEnd:
    account_id: str | None
    model_source_id: str | None
    ends_at: datetime


class AccountSubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ends(self) -> list[AccountSubscriptionEnd]:
        accounts = await self._session.execute(
            select(Account.id, Account.subscription_ends_at).where(
                Account.delete_requested_at.is_(None),
                Account.subscription_ends_at.is_not(None),
            )
        )
        sources = await self._session.execute(
            select(ModelSource.id, ModelSource.subscription_ends_at).where(
                ModelSource.kind.in_(SUBSCRIPTION_SOURCE_KINDS),
                ModelSource.subscription_ends_at.is_not(None),
            )
        )
        return [
            *(AccountSubscriptionEnd(row.id, None, row.subscription_ends_at) for row in accounts),
            *(AccountSubscriptionEnd(None, row.id, row.subscription_ends_at) for row in sources),
        ]

    async def set_account_end(self, account_id: str, ends_at: datetime | None) -> bool:
        async with sqlite_writer_section():
            result = await self._session.execute(
                update(Account)
                .where(Account.id == account_id)
                .where(Account.delete_requested_at.is_(None))
                .values(subscription_ends_at=_stored(ends_at))
                .returning(Account.id)
            )
            await self._session.commit()
            return result.scalar_one_or_none() is not None

    async def set_model_source_end(self, source_id: str, ends_at: datetime | None) -> SourceUpdateResult:
        kind = await self._session.scalar(select(ModelSource.kind).where(ModelSource.id == source_id))
        if kind is None:
            return "not_found"
        if kind not in SUBSCRIPTION_SOURCE_KINDS:
            return "not_applicable"
        async with sqlite_writer_section():
            await self._session.execute(
                update(ModelSource).where(ModelSource.id == source_id).values(subscription_ends_at=_stored(ends_at))
            )
            await self._session.commit()
        return "updated"


def _stored(ends_at: datetime | None) -> datetime | None:
    return to_utc_naive(ends_at) if ends_at is not None else None
