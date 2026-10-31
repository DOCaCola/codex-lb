from __future__ import annotations

import pytest
from alembic import command
from anyio import to_thread
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.migrate import _build_alembic_config, run_upgrade

pytestmark = pytest.mark.unit

PARENT = "20261029_000000_antigravity_accounts"
REVISION = "20261031_000000_claude_plan_rename"
INSERT = text("INSERT INTO request_logs (request_id, model, status, plan_type) VALUES (:id, 'm', 'success', :plan)")


@pytest.mark.asyncio
async def test_plan_rename_migration_renames_recorded_snapshots_and_downgrade_restores_them(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'plans.sqlite'}"

    async def plans(engine) -> list[str | None]:
        async with engine.connect() as connection:
            return list((await connection.execute(text("SELECT plan_type FROM request_logs ORDER BY id"))).scalars())

    await to_thread.run_sync(lambda: run_upgrade(db_url, PARENT, bootstrap_legacy=False))
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as connection:
            for plan in ("max_5x", "max_20x", "pro", "plus", None):
                await connection.execute(INSERT, {"id": f"req-{plan}", "plan": plan})

        await to_thread.run_sync(lambda: run_upgrade(db_url, REVISION, bootstrap_legacy=False))
        assert await plans(engine) == ["max", "ultra", "pro", "plus", None]

        await to_thread.run_sync(lambda: command.downgrade(_build_alembic_config(db_url), PARENT))
        assert await plans(engine) == ["max_5x", "max_20x", "pro", "plus", None]
    finally:
        await engine.dispose()
