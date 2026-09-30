from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic import command

from app.core.utils.time import utcnow
from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade
from app.db.models import Account
from app.db.session import SessionLocal
from app.modules.proxy._service.support import _http_bridge_session_supports_service_tier
from app.modules.proxy.account_cache import (
    RoutingAvailabilityCache,
    get_routing_availability_cache,
    is_account_model_allowed,
)
from app.modules.proxy.load_balancer import LoadBalancer
from tests.integration.test_load_balancer_integration import _repo_factory

pytestmark = pytest.mark.integration


def account(account_id):
    return Account(
        id=account_id,
        email="test@example.invalid",
        plan_type="pro",
        last_refresh=utcnow(),
        access_token_encrypted=b"a",
        refresh_token_encrypted=b"r",
        id_token_encrypted=b"i",
    )


async def test_native_mode_api_retains_selection_and_enforces_fresh_and_warm_routing(async_client):
    async with SessionLocal() as session:
        session.add(account("native"))
        await session.commit()
        stale = await session.get(Account, "native")
        session.expunge(stale)
    path = "/api/accounts/native/models"
    initial = await async_client.get(path)
    assert initial.status_code == 200, initial.text
    assert initial.json()["allModels"] is True
    selected = initial.json()["catalog"][0]["model"]
    payload = {"allModels": False, "selectedModels": [selected]}
    response = await async_client.put(path, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["selectedModels"] == [selected]
    public = await async_client.get("/v1/models")
    assert {model["id"] for model in public.json()["data"]} == {selected}
    codex = await async_client.get("/backend-api/codex/models")
    assert {model["slug"] for model in codex.json()["models"] if model["visibility"] == "list"} == {selected}
    balancer = LoadBalancer(_repo_factory)
    allowed = await balancer.select_account(model=selected)
    assert allowed.account and allowed.account.id == "native"
    denied = await balancer.select_account(model="unadvertised-mapped-model")
    assert denied.account is None
    pinned = await balancer.select_account(
        model="unadvertised-mapped-model", required_account_id="native", required_account_is_ownership_constraint=True
    )
    assert pinned.account is None
    bridge = SimpleNamespace(account=stale)
    assert not _http_bridge_session_supports_service_tier(
        bridge, request_model="unadvertised-mapped-model", request_service_tier=None
    )
    assert is_account_model_allowed(stale, selected)
    await get_routing_availability_cache().refresh_from_db()
    assert not is_account_model_allowed(stale, "unadvertised-mapped-model")
    enabled = await async_client.put(path, json={**payload, "allModels": True})
    assert enabled.json()["selectedModels"] == [selected]
    assert is_account_model_allowed(stale, "unadvertised-mapped-model")
    restored = await async_client.put(path, json=payload)
    assert restored.json()["selectedModels"] == [selected]
    invalid = await async_client.put(path, json={"allModels": False, "selectedModels": ["invented"]})
    assert invalid.status_code == 400
    duplicate = await async_client.put(path, json={"allModels": False, "selectedModels": [selected, selected]})
    assert duplicate.status_code == 400


async def test_native_mode_change_on_other_replica_replaces_local_policy(async_client):
    async with SessionLocal() as session:
        session.add(account("replica"))
        await session.commit()
        stale = await session.get(Account, "replica")
        session.expunge(stale)
    cache = get_routing_availability_cache()
    cache.set_model_selection("replica", False, [])
    await cache.refresh_from_db()
    assert is_account_model_allowed(stale, "any-model")


async def test_repeated_model_restriction_during_snapshot_refresh_remains_effective(monkeypatch):
    async with SessionLocal() as session:
        row = account("model-policy-race")
        session.add(row)
        await session.commit()
        session.expunge(row)
    repeat = True

    def factory():
        session = SessionLocal()
        execute = session.execute

        async def read_then_repeat(*args, **kwargs):
            nonlocal repeat
            result = await execute(*args, **kwargs)
            if repeat:
                repeat = False
                cache.set_model_selection(row.id, False, [])
            return result

        monkeypatch.setattr(session, "execute", read_then_repeat)
        return session

    cache = RoutingAvailabilityCache(factory)
    cache.set_model_selection(row.id, False, [])
    await cache.refresh_from_db()
    assert cache.model_selection(row) == (False, ())
    await cache.refresh_from_db()
    assert cache.model_selection(row) == (True, ())


def test_account_controls_migration_defaults_and_roundtrip(tmp_path):
    url = f"sqlite:///{tmp_path / 'controls.db'}"
    parent = "20260930_000000_claude_quota_deadlines"
    run_upgrade(url, parent, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO accounts (id, email, plan_type, access_token_encrypted, "
                    "refresh_token_encrypted, id_token_encrypted, last_refresh, codex_installation_id, status) "
                    "VALUES ('legacy', 'test@example.invalid', 'pro', X'01', X'02', X'03', "
                    "CURRENT_TIMESTAMP, 'test', 'active')"
                )
            )
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.connect() as connection:
            assert connection.execute(
                sa.text("SELECT all_models, selected_models FROM accounts WHERE id='legacy'")
            ).one() == (1, "[]")
        assert check_schema_drift(url) == ()
        command.downgrade(_build_alembic_config(url), parent)
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
