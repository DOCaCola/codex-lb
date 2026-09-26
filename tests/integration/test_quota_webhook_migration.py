from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade


def test_webhook_migration_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 'webhook-migration.db'}"
    config = _build_alembic_config(url)
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    run_upgrade(url, bootstrap_legacy=False)
    assert check_schema_drift(url) == ()
    engine = create_engine(url)
    try:
        assert "quota_webhook_config" in inspect(engine).get_table_names()
        command.downgrade(config, "20260925_030000_claude_identity")
        assert "quota_webhook_config" not in inspect(engine).get_table_names()
        run_upgrade(url, bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
