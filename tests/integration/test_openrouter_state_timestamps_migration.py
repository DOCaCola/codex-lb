import json

import sqlalchemy as sa
from alembic import command

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade
from app.modules.openrouter.schemas import AccountState

PARENT = "20261126_000000_openai_api_accounts"


def test_naive_openrouter_observation_times_become_utc(tmp_path):
    url = f"sqlite:///{tmp_path / 'openrouter-timestamps.db'}"
    run_upgrade(url, PARENT, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    sources = sa.Table("model_sources", metadata, autoload_with=engine)
    accounts = sa.Table("openrouter_accounts", metadata, autoload_with=engine)
    state = {
        "catalog_updated_at": "2026-11-26T09:15:00.123456",
        "key_updated_at": "2026-11-26T09:16:00",
        "credits_updated_at": None,
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

        def stored() -> dict:
            with engine.connect() as connection:
                return json.loads(connection.scalar(sa.select(accounts.c.state_json)))

        run_upgrade(url, "head", bootstrap_legacy=False)
        upgraded = stored()
        assert upgraded == {
            "catalog_updated_at": "2026-11-26T09:15:00.123456Z",
            "key_updated_at": "2026-11-26T09:16:00Z",
            "credits_updated_at": None,
            "key_error": "retained",
        }
        AccountState.model_validate(upgraded)

        command.downgrade(_build_alembic_config(url), PARENT)
        assert stored() == state
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert stored() == upgraded
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
