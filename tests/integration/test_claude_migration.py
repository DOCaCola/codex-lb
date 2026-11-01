from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade


def test_claude_migration_single_head_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 'claude-migration.db'}"
    config = _build_alembic_config(url)
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    run_upgrade(url, bootstrap_legacy=False)
    assert check_schema_drift(url) == ()
    engine = create_engine(url)
    try:
        assert {"claude_accounts", "claude_oauth_flows", "claude_version_state"} <= set(
            inspect(engine).get_table_names()
        )
        command.downgrade(config, "20260925_000000_openrouter_accounts")
        assert "claude_accounts" not in inspect(engine).get_table_names()
        assert "openrouter_accounts" in inspect(engine).get_table_names()
        run_upgrade(url, bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()


def test_claude_build_migration_resets_unverified_versions(tmp_path):
    url = f"sqlite:///{tmp_path / 'claude-builds.db'}"
    config = _build_alembic_config(url)
    command.upgrade(config, "20261031_040000_quota_webhook_redeemed_kind")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO claude_version_state (id, discovered_version, pinned_version, etag, last_checked_at) "
                    "VALUES (1, '2.1.300', '2.1.280', '\"release\"', '2026-10-31 00:00:00')"
                )
            )
        command.upgrade(config, "20261101_000000_claude_client_builds")
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT discovered_version, pinned_version, etag, last_checked_at FROM claude_version_state")
            ).one()
        # The release check runs again and verifies 2.1.300 or anything newer than the baseline.
        assert tuple(row) == ("2.1.316", None, None, None)
    finally:
        engine.dispose()
