import json
from datetime import datetime

import sqlalchemy as sa
from alembic import command

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

PARENT = "20260929_020000_merge_upstream_routing_heads"


def test_old_manual_limits_removed_without_touching_other_sources(tmp_path):
    url = f"sqlite:///{tmp_path / 'limits.db'}"
    run_upgrade(url, PARENT, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    sources = sa.Table("model_sources", metadata, autoload_with=engine)
    accounts = sa.Table("claude_accounts", metadata, autoload_with=engine)
    models = sa.Table("model_source_models", metadata, autoload_with=engine)
    state = {
        "selections": [{"model": "claude-opus-5", "context_window": 200000, "max_output_tokens": 8192}],
        "catalog_updated_at": "2026-09-29T00:00:00Z",
        "catalog": [],
        "usage_error": "retained",
    }
    try:
        with engine.begin() as connection:
            for identifier, kind in [("claude", "claude"), ("other", "openrouter")]:
                connection.execute(
                    sources.insert().values(id=identifier, name=identifier, kind=kind, base_url="https://example.com")
                )
                connection.execute(
                    models.insert().values(
                        source_id=identifier,
                        model="example",
                        context_window=200000,
                        max_output_tokens=8192,
                        is_enabled=True,
                    )
                )
            connection.execute(
                accounts.insert().values(
                    source_id="claude",
                    credentials_encrypted=b"not-a-real-key",
                    grant_fingerprint="test",
                    expires_at=datetime(2026, 10, 1),
                    state_json=json.dumps(state),
                )
            )
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.connect() as connection:
            stored_json = connection.scalar(sa.select(accounts.c.state_json))
            assert isinstance(stored_json, str)
            stored = json.loads(stored_json)
            assert stored["selections"] == [{"model": "claude-opus-5"}]
            assert stored["catalog_updated_at"] is None
            assert stored["usage_error"] == "retained"
            assert connection.scalar(sa.text("SELECT routing_policy FROM claude_accounts")) == "normal"
            rows = {row.source_id: row for row in connection.execute(sa.select(models))}
            assert not rows["claude"].is_enabled and rows["claude"].context_window is None
            assert rows["claude"].max_output_tokens is None
            assert rows["other"].is_enabled and rows["other"].max_output_tokens == 8192
        command.downgrade(_build_alembic_config(url), PARENT)
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
