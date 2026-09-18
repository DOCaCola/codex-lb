"""Upgrade published branches without renaming their deployed revision IDs."""

from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration
PARENT = "20260913_000000_add_oidc_provider_flow"
SCIM = "20260914_000000_add_scim_tokens"
RETIRE = "20260914_000000_drop_subscription_overflow_schema"
MERGE = "20260919_000000_merge_scim_overflow_heads"


@pytest.mark.parametrize("branches", [(), (SCIM,), (RETIRE,), (SCIM, RETIRE), (RETIRE, SCIM)])
def test_upgrade_and_schema_rollback(tmp_path: Path, branches: tuple[str, ...]) -> None:
    path = tmp_path / "branches.sqlite"
    url = f"sqlite+aiosqlite:///{path}"
    engine = create_engine(f"sqlite:///{path}")
    config = _build_alembic_config(url)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [MERGE]
    assert script.get_revision(MERGE).down_revision == (SCIM, RETIRE)
    assert script.get_revision(SCIM).down_revision == PARENT
    assert script.get_revision(RETIRE).down_revision == PARENT
    try:
        run_upgrade(url, PARENT, bootstrap_legacy=False)
        with engine.begin() as connection:
            connection.execute(text("UPDATE dashboard_settings SET upstream_stream_transport='http' WHERE id=1"))
        for revision in branches:
            run_upgrade(url, revision, bootstrap_legacy=False)
        if SCIM in branches:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO dashboard_scim_tokens (id,label,token_hash,token_prefix,provider_key) "
                        "VALUES ('retained-token','Test','digest','scim_test','test-provider')"
                    )
                )
        assert run_upgrade(url, "head", bootstrap_legacy=False).current_revision == MERGE
        assert check_schema_drift(url) == ()
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT upstream_stream_transport FROM dashboard_settings WHERE id=1")) == "http"
            )
            assert not inspect(connection).has_table("model_source_pins")
            if SCIM in branches:
                assert (
                    connection.scalar(text("SELECT token_hash FROM dashboard_scim_tokens WHERE id='retained-token'"))
                    == "digest"
                )

        for branch in (SCIM, RETIRE):
            command.downgrade(config, branch)
            with engine.connect() as connection:
                assert set(connection.scalars(text("SELECT version_num FROM alembic_version"))) == {SCIM, RETIRE}
                assert inspect(connection).has_table("dashboard_scim_tokens")
                assert not inspect(connection).has_table("model_source_pins")
            run_upgrade(url, "head", bootstrap_legacy=False)

        # Actual schema rollback requires both parents' downgrade code, not
        # merely removing the merge stamp or switching to the old image.
        command.downgrade(config, PARENT)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PARENT
            inspector = inspect(connection)
            assert inspector.has_table("model_source_pins")
            assert not inspector.has_table("dashboard_scim_tokens")
            columns = {column["name"] for column in inspector.get_columns("dashboard_settings")}
            assert {"subscription_overflow_source_id", "subscription_overflow_drain_until"} <= columns
            assert (
                connection.scalar(text("SELECT upstream_stream_transport FROM dashboard_settings WHERE id=1")) == "http"
            )
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
