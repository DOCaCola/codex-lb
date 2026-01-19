from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession


def _request_logs_column_state(conn: Connection) -> tuple[bool, bool]:
    inspector = inspect(conn)
    if not inspector.has_table("request_logs"):
        return False, False
    columns = {column["name"] for column in inspector.get_columns("request_logs")}
    return True, "reasoning_effort" in columns


async def run(session: AsyncSession) -> None:
    conn = await session.connection()
    has_table, has_column = await conn.run_sync(_request_logs_column_state)
    if not has_table or has_column:
        return
    await session.execute(text("ALTER TABLE request_logs ADD COLUMN reasoning_effort VARCHAR"))
