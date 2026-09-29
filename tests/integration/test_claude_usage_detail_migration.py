import sqlalchemy as sa
from alembic import command

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

PARENT = "20260929_030000_claude_automatic_limits"


def test_claude_usage_columns_keep_historical_unknowns_through_downgrade_upgrade(tmp_path):
    url = f"sqlite:///{tmp_path / 'claude-usage.db'}"
    run_upgrade(url, PARENT, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO request_logs "
                    "(request_id, model, status, input_tokens, output_tokens, cached_input_tokens) "
                    "VALUES ('historic', 'anthropic/claude-haiku-4-5-20251001', 'success', 100, 2, 0)"
                )
            )
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.connect() as connection:
            detail = connection.execute(
                sa.text(
                    "SELECT cache_creation_tokens, cache_creation_5m_tokens, cache_creation_1h_tokens, "
                    "upstream_thinking_mode, upstream_thinking_budget_tokens, cost_provenance FROM request_logs "
                    "WHERE request_id='historic'"
                )
            ).one()
            assert detail == (None, None, None, None, None, None)
        command.downgrade(_build_alembic_config(url), PARENT)
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
