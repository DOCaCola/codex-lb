from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade


def test_claude_migration_single_head_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 'claude-migration.db'}"
    config = _build_alembic_config(url)
    assert ScriptDirectory.from_config(config).get_heads() == ["20260925_010000_claude_accounts"]
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
