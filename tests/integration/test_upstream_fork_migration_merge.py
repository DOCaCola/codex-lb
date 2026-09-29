import pytest
from alembic import command
from anyio import to_thread
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration
FORK = "20260929_010000_claude_routing"
UPSTREAM = "20260918_000000_merge_scim_and_overflow_heads"
MERGE = "20260929_020000_merge_upstream_routing_heads"


@pytest.mark.parametrize("start", ["base", FORK, UPSTREAM])
async def test_upstream_fork_heads_converge(tmp_path, start):
    url = f"sqlite+aiosqlite:///{tmp_path / 'merge.db'}"
    await to_thread.run_sync(lambda: run_upgrade(url, start, bootstrap_legacy=False))
    await to_thread.run_sync(lambda: run_upgrade(url, "head", bootstrap_legacy=False))
    assert not await to_thread.run_sync(lambda: check_schema_drift(url))
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            assert list(await connection.scalars(text("SELECT version_num FROM alembic_version"))) == [MERGE]
        # One-step downgrade only removes the new no-op convergence stamp.
        await to_thread.run_sync(lambda: command.downgrade(_build_alembic_config(url), FORK))
        async with engine.connect() as connection:
            assert set(await connection.scalars(text("SELECT version_num FROM alembic_version"))) == {FORK, UPSTREAM}
        assert not await to_thread.run_sync(lambda: check_schema_drift(url))
        await to_thread.run_sync(lambda: run_upgrade(url, "head", bootstrap_legacy=False))
    finally:
        await engine.dispose()
