from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Insert, func

from app.db.models import StickySession


class StickySessionsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_account_id(self, key: str) -> str | None:
        if not key:
            return None
        result = await self._session.execute(select(StickySession.account_id).where(StickySession.key == key))
        return result.scalar_one_or_none()

    async def upsert(self, key: str, account_id: str) -> StickySession:
        statement = self._build_upsert_statement(key, account_id)
        await self._session.execute(statement)
        await self._session.commit()
        row = await self._session.get(StickySession, key)
        if row is None:
            raise RuntimeError(f"StickySession upsert failed for key={key!r}")
        await self._session.refresh(row)
        return row

    async def delete(self, key: str) -> bool:
        if not key:
            return False
        result = await self._session.execute(
            delete(StickySession).where(StickySession.key == key).returning(StickySession.key)
        )
        await self._session.commit()
        return result.scalar_one_or_none() is not None

    def _build_upsert_statement(self, key: str, account_id: str) -> Insert:
        dialect = self._session.get_bind().dialect.name
        if dialect == "postgresql":
            insert_fn = pg_insert
        elif dialect == "sqlite":
            insert_fn = sqlite_insert
        else:
            raise RuntimeError(f"StickySession upsert unsupported for dialect={dialect!r}")
        statement = insert_fn(StickySession).values(key=key, account_id=account_id)
        return statement.on_conflict_do_update(
            index_elements=[StickySession.key],
            set_={
                "account_id": account_id,
                "updated_at": func.now(),
            },
        )
