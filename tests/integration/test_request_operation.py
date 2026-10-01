import pytest
import sqlalchemy as sa
from alembic import command

from app.core.clients.proxy import CodexControlResponse, ProxyResponseError
from app.core.usage.request_operation import RequestOperation
from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade
from app.db.models import RequestLog
from app.db.session import SessionLocal
from app.dependencies import get_proxy_service_for_app
from app.modules.proxy import service as proxy_module
from app.modules.request_logs.repository import RequestLogsRepository
from tests.integration.test_proxy_api_extended import _import_account

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize(
    "method,endpoint,operation",
    [
        ("POST", "alpha/search", "web_search"),
        ("POST", "analytics-events/events", "analytics"),
        ("POST", "memories/trace_summarize", "memory_summary"),
        ("POST", "safety/arc", "safety"),
        ("GET", "agent-identities/jwks", "identity_keys"),
    ],
)
async def test_control_operation_is_logged_and_exposed(async_client, monkeypatch, method, endpoint, operation, failed):
    await _import_account(async_client, "operation-test", "operation@test.example")

    async def fake_control(*args, **kwargs):
        if failed:
            raise ProxyResponseError(400, {"error": {"code": "invalid_request_error", "message": "Test refusal"}})
        return CodexControlResponse(200, b'{"ok":true}', {"content-type": "application/json"})

    monkeypatch.setattr(proxy_module, "core_codex_control_request", fake_control)
    response = await async_client.request(
        method,
        f"/backend-api/codex/{endpoint}",
        json={} if method == "POST" else None,
        headers={"x-request-id": "operation-test", "x-codex-bridge-request-operation": "responses"},
    )
    assert response.status_code == (400 if failed else 200)
    from app.main import app

    await get_proxy_service_for_app(app).drain_persistence_tasks(timeout_seconds=2)
    async with SessionLocal() as session:
        row = (
            await session.execute(sa.select(RequestLog).where(RequestLog.request_id == "operation-test"))
        ).scalar_one()
        assert row.request_operation == operation
        assert row.request_kind == "normal"
        assert row.model == ""
        assert row.input_tokens is None and row.output_tokens is None and row.cost_usd is None
    logs = await async_client.get("/api/request-logs")
    assert logs.status_code == 200
    entry = next(row for row in logs.json()["requests"] if row["requestId"] == "operation-test")
    assert entry["requestOperation"] == operation


@pytest.mark.asyncio
async def test_historical_operation_stays_unknown_and_workload_keeps_coverage_rules(async_client, db_setup):
    async with SessionLocal() as session:
        repo = RequestLogsRepository(session)
        for request_id, operation, kind in [
            ("historical", None, "normal"),
            ("count", RequestOperation.COUNT_TOKENS, "count_tokens"),
        ]:
            await repo.add_log(
                account_id=None,
                request_id=request_id,
                model="claude-test",
                input_tokens=None,
                output_tokens=None,
                latency_ms=10,
                status="success",
                error_code=None,
                request_operation=operation,
                request_kind=kind,
            )
    result = (await async_client.get("/api/request-logs")).json()
    entries = {row["requestId"]: row for row in result["requests"]}
    assert entries["historical"]["requestOperation"] is None
    assert entries["count"]["requestOperation"] == "count_tokens"
    assert entries["count"]["requestKind"] == "count_tokens"
    assert result["costCoverage"]["unmeteredRequests"] == 1


def test_operation_migration_retains_populated_logs_and_roundtrips(tmp_path):
    url = f"sqlite:///{tmp_path / 'operations.db'}"
    parent = "20260930_030000_account_reserve_usage"
    run_upgrade(url, parent, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("INSERT INTO request_logs (request_id, model, status) VALUES ('old', '', 'success')")
            )
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT request_operation FROM request_logs WHERE request_id='old'")
                ).scalar()
                is None
            )
        command.downgrade(_build_alembic_config(url), parent)
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
        with engine.connect() as connection:
            assert connection.execute(sa.text("SELECT COUNT(*) FROM request_logs WHERE request_id='old'")).scalar() == 1
    finally:
        engine.dispose()
