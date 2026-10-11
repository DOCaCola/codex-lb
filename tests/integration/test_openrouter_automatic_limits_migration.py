import json

import sqlalchemy as sa
from alembic import command

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

PARENT = "20261009_000000_drop_anonymous_telemetry"


def test_openrouter_selection_caps_removed_and_catalog_marked_stale(tmp_path):
    url = f"sqlite:///{tmp_path / 'openrouter-limits.db'}"
    run_upgrade(url, PARENT, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    sources = sa.Table("model_sources", metadata, autoload_with=engine)
    accounts = sa.Table("openrouter_accounts", metadata, autoload_with=engine)
    state = {
        "all_models": False,
        "selections": [
            {"model": "z-ai/glm-5.3-flash", "context_window": 262144, "max_output_tokens": None, "display_name": None},
            {"model": "vendor/named", "context_window": 100000, "max_output_tokens": 8192, "display_name": "Named"},
        ],
        "catalog_updated_at": "2026-10-10T00:00:00Z",
        "catalog": [],
        "key_error": "retained",
    }
    try:
        with engine.begin() as connection:
            connection.execute(
                sources.insert().values(
                    id="router", name="router", kind="openrouter", base_url="https://openrouter.ai/api/v1"
                )
            )
            connection.execute(accounts.insert().values(source_id="router", state_json=json.dumps(state)))
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.connect() as connection:
            stored_json = connection.scalar(sa.select(accounts.c.state_json))
            assert isinstance(stored_json, str)
            stored = json.loads(stored_json)
            assert stored["selections"] == [
                {"model": "z-ai/glm-5.3-flash", "display_name": None},
                {"model": "vendor/named", "display_name": "Named"},
            ]
            assert stored["catalog_updated_at"] is None
            assert stored["key_error"] == "retained"
        command.downgrade(_build_alembic_config(url), PARENT)
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
