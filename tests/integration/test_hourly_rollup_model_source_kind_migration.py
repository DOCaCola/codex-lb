from datetime import datetime

import sqlalchemy as sa
from alembic import command

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

PARENT = "20261011_000000_openrouter_automatic_limits"
SENTINEL = "\x1f"


def _row(**overrides):
    return {
        "bucket_epoch": 3600,
        "account_id": SENTINEL,
        "api_key_id": "key",
        "model": "model",
        "service_tier": SENTINEL,
        "request_kind": "normal",
        "is_deleted": False,
        "request_count": 1,
        "input_tokens": 10,
        **overrides,
    }


def test_hourly_rollups_gain_source_kind_and_refold(tmp_path):
    url = f"sqlite:///{tmp_path / 'hourly-kind.db'}"
    run_upgrade(url, PARENT, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    try:
        metadata = sa.MetaData()
        state = sa.Table("account_usage_rollup_state", metadata, autoload_with=engine)
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM account_usage_rollup_state"))
            connection.execute(
                state.insert().values(
                    id=1,
                    folded_through=datetime(1970, 1, 1),
                    hourly_folded_through=datetime(2026, 10, 1),
                    upgrade_repair_from=None,
                )
            )
            rollups = sa.Table("request_usage_hourly_rollups", sa.MetaData(), autoload_with=connection)
            connection.execute(rollups.insert().values(_row()))
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.connect() as connection:
            assert connection.execute(sa.text("SELECT model_source_kind FROM request_usage_hourly_rollups")).all() == [
                (SENTINEL,)
            ]
            assert connection.scalar(sa.select(state.c.upgrade_repair_from)) == datetime(1970, 1, 1)
        with engine.begin() as connection:
            rollups = sa.Table("request_usage_hourly_rollups", sa.MetaData(), autoload_with=connection)
            connection.execute(rollups.insert().values(_row(model_source_kind="claude", input_tokens=5)))
        command.downgrade(_build_alembic_config(url), PARENT)
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT request_count, input_tokens FROM request_usage_hourly_rollups")
            ).all() == [(2, 15)]
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
