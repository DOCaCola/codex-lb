import sqlalchemy as sa
from alembic import command

from app.db.migrate import _build_alembic_config


def test_resource_migration_no_guessed_backfill(tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = _build_alembic_config(url)
    parent = "20260928_010000_claude_reset_grants"
    head = "20260929_000000_claude_resource_origins"
    command.upgrade(config, parent)
    engine = sa.create_engine(url)
    command.upgrade(config, head)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM claude_resource_origins").scalar() == 0
        assert sa.inspect(connection).get_foreign_keys("claude_resource_origins")[0]["options"]["ondelete"] == "CASCADE"
    command.downgrade(config, parent)
    with engine.connect() as connection:
        assert "claude_resource_origins" not in sa.inspect(connection).get_table_names()
    command.upgrade(config, head)
    engine.dispose()
