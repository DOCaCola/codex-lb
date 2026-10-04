"""Chart colours of provider accounts (Codex accounts and model sources).

Colours are indices into the dashboard chart palette. An operator pick wins;
every other live account takes the first palette index no pick claims, in
creation order, so an account keeps its colour on every chart.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from itertools import chain, cycle

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ModelSource
from app.db.session import sqlite_writer_section

#: Selectable palette entries: the six base chart colours and their first six shades.
PALETTE_SIZE = 12


@dataclass(frozen=True, slots=True)
class AccountColor:
    account_id: str | None
    model_source_id: str | None
    chart_color: int | None
    color: int
    automatic_color: int


@dataclass(frozen=True, slots=True)
class ColorMember:
    account_id: str | None
    model_source_id: str | None
    chart_color: int | None


def _assign(members: Sequence[ColorMember]) -> list[int]:
    picked = {member.chart_color for member in members if member.chart_color is not None}
    free: Iterator[int] = chain(
        (index for index in range(PALETTE_SIZE) if index not in picked),
        cycle(range(PALETTE_SIZE)),
    )
    return [member.chart_color if member.chart_color is not None else next(free) for member in members]


def resolve_colors(members: Sequence[ColorMember]) -> list[AccountColor]:
    """Effective colour of every member, plus the colour it would get without its pick."""

    colors = _assign(members)
    resolved: list[AccountColor] = []
    for position, member in enumerate(members):
        automatic = colors[position]
        if member.chart_color is not None:
            unpinned = [*members[:position], replace(member, chart_color=None), *members[position + 1 :]]
            automatic = _assign(unpinned)[position]
        resolved.append(
            AccountColor(
                account_id=member.account_id,
                model_source_id=member.model_source_id,
                chart_color=member.chart_color,
                color=colors[position],
                automatic_color=automatic,
            )
        )
    return resolved


class AccountColorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def colors(self) -> list[AccountColor]:
        accounts = await self._session.execute(
            select(Account.id, Account.chart_color, Account.created_at).where(Account.delete_requested_at.is_(None))
        )
        sources = await self._session.execute(select(ModelSource.id, ModelSource.chart_color, ModelSource.created_at))
        ordered = sorted(
            [
                *((row.created_at, row.id, ColorMember(row.id, None, row.chart_color)) for row in accounts),
                *((row.created_at, row.id, ColorMember(None, row.id, row.chart_color)) for row in sources),
            ],
            key=lambda entry: (entry[0], entry[1]),
        )
        return resolve_colors([member for _, _, member in ordered])

    async def set_account_color(self, account_id: str, chart_color: int | None) -> bool:
        async with sqlite_writer_section():
            result = await self._session.execute(
                update(Account)
                .where(Account.id == account_id)
                .where(Account.delete_requested_at.is_(None))
                .values(chart_color=chart_color)
                .returning(Account.id)
            )
            await self._session.commit()
            return result.scalar_one_or_none() is not None

    async def set_model_source_color(self, source_id: str, chart_color: int | None) -> bool:
        async with sqlite_writer_section():
            result = await self._session.execute(
                update(ModelSource)
                .where(ModelSource.id == source_id)
                .values(chart_color=chart_color)
                .returning(ModelSource.id)
            )
            await self._session.commit()
            return result.scalar_one_or_none() is not None
