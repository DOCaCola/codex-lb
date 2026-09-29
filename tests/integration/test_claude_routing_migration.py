import pytest
from alembic import command
from anyio import to_thread
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration
PARENT = "20260929_000000_claude_resource_origins"
REVISION = "20260929_010000_claude_routing"


async def test_claude_routing_migration_roundtrip(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'routing.db'}"
    await to_thread.run_sync(lambda: run_upgrade(url, PARENT, bootstrap_legacy=False))
    engine = create_async_engine(url)

    async def check(present):
        async with engine.connect() as connection:
            for table, column in (
                ("dashboard_settings", "claude_single_account_id"),
                ("claude_accounts", "last_selected_at"),
            ):
                columns = await connection.run_sync(lambda conn: inspect(conn).get_columns(table))
                assert (column in {item["name"] for item in columns}) is present
                if present:
                    assert next(item for item in columns if item["name"] == column)["nullable"]

    try:
        await check(False)
        await to_thread.run_sync(lambda: run_upgrade(url, REVISION, bootstrap_legacy=False))
        await check(True)
        await to_thread.run_sync(lambda: command.downgrade(_build_alembic_config(url), PARENT))
        await check(False)
        await to_thread.run_sync(lambda: run_upgrade(url, "head", bootstrap_legacy=False))
        await check(True)
        assert not await to_thread.run_sync(lambda: check_schema_drift(url))
    finally:
        await engine.dispose()
