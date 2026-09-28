import sqlalchemy as sa
from alembic import command

from app.db.migrate import _build_alembic_config


def test_reset_migration_preserves_unknown_cooldowns(tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = _build_alembic_config(url)
    command.upgrade(config, "20260928_000000_claude_cooldowns")
    engine = sa.create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO claude_cooldowns(source_id, model, until) VALUES ('historical', '*', '2026-10-01 00:00:00')"
        )
    command.upgrade(config, "20260928_010000_claude_reset_grants")
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT evidence_json FROM claude_cooldowns").scalar() is None
        assert "claude_reset_operations" in sa.inspect(connection).get_table_names()
    command.downgrade(config, "20260928_000000_claude_cooldowns")
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM claude_cooldowns").scalar() == 1
    command.upgrade(config, "20260928_010000_claude_reset_grants")
    engine.dispose()
