"""Operator notes on provider accounts (Codex accounts and model sources)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ModelSource
from app.db.session import sqlite_writer_section

MAX_NOTE_LENGTH = 2000


@dataclass(frozen=True, slots=True)
class AccountNote:
    account_id: str | None
    model_source_id: str | None
    note: str


def normalize_note(note: str | None) -> str | None:
    """Trim surrounding whitespace; an empty note is no note."""
    if note is None:
        return None
    return note.strip() or None


class AccountNoteService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def notes(self) -> list[AccountNote]:
        accounts = await self._session.execute(
            select(Account.id, Account.note).where(
                Account.delete_requested_at.is_(None),
                Account.note.is_not(None),
            )
        )
        sources = await self._session.execute(
            select(ModelSource.id, ModelSource.note).where(ModelSource.note.is_not(None))
        )
        return [
            *(AccountNote(row.id, None, row.note) for row in accounts),
            *(AccountNote(None, row.id, row.note) for row in sources),
        ]

    async def set_account_note(self, account_id: str, note: str | None) -> bool:
        async with sqlite_writer_section():
            result = await self._session.execute(
                update(Account)
                .where(Account.id == account_id)
                .where(Account.delete_requested_at.is_(None))
                .values(note=normalize_note(note))
                .returning(Account.id)
            )
            await self._session.commit()
            return result.scalar_one_or_none() is not None

    async def set_model_source_note(self, source_id: str, note: str | None) -> bool:
        async with sqlite_writer_section():
            result = await self._session.execute(
                update(ModelSource)
                .where(ModelSource.id == source_id)
                .values(note=normalize_note(note))
                .returning(ModelSource.id)
            )
            await self._session.commit()
            return result.scalar_one_or_none() is not None
