from __future__ import annotations

import pytest
from alembic import command
from anyio import to_thread
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.migrate import _build_alembic_config, inspect_migration_state, run_upgrade

pytestmark = pytest.mark.unit

TELEMETRY_COLUMNS = {
    "telemetry_consent",
    "telemetry_instance_id",
    "telemetry_private_key_encrypted",
}


@pytest.mark.asyncio
async def test_drop_telemetry_migration_removes_columns_and_downgrade_restores_them(tmp_path) -> None:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'telemetry.sqlite'}"
    parent = "20261006_000000_claude_quota_provenance"

    async def columns(engine) -> set[str]:
        async with engine.connect() as connection:
            return {row[1] for row in await connection.execute(text("PRAGMA table_info('dashboard_settings')"))}

    await to_thread.run_sync(lambda: run_upgrade(db_url, parent, bootstrap_legacy=False))
    engine = create_async_engine(db_url)
    try:
        assert TELEMETRY_COLUMNS <= await columns(engine)

        result = await to_thread.run_sync(lambda: run_upgrade(db_url, "head", bootstrap_legacy=False))
        assert result.current_revision == inspect_migration_state(db_url).head_revision
        assert not TELEMETRY_COLUMNS & await columns(engine)

        await to_thread.run_sync(lambda: command.downgrade(_build_alembic_config(db_url), parent))
        assert TELEMETRY_COLUMNS <= await columns(engine)
        async with engine.connect() as connection:
            rows = (
                await connection.execute(
                    text(
                        "SELECT telemetry_consent, telemetry_instance_id, "
                        "telemetry_private_key_encrypted FROM dashboard_settings"
                    )
                )
            ).all()
        assert all(row == ("undecided", None, None) for row in rows)
    finally:
        await engine.dispose()
