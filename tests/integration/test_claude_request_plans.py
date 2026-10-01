from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.db.models import ClaudeAccount, RequestLog
from app.db.session import SessionLocal
from app.modules.claude.schemas import AccountState, SubscriptionMetadata
from tests.integration import test_claude_routing as routing_fixtures
from tests.integration.test_claude_inference import install_upstream, native_headers

pytestmark = pytest.mark.integration
pool = routing_fixtures.pool
MODEL = routing_fixtures.MODEL


async def set_plan(source_ids, plan):
    async with SessionLocal() as session:
        for source_id in source_ids:
            account = await session.get(ClaudeAccount, source_id)
            state = AccountState.model_validate_json(account.state_json)
            state.subscription = (
                SubscriptionMetadata(subscription_type=plan, source="bootstrap", observed_at=datetime.now(UTC))
                if plan is not None
                else None
            )
            account.state_json = state.model_dump_json()
        await session.commit()


@pytest.mark.parametrize(
    "path", ["/v1/messages", "/v1/responses", "/backend-api/codex/responses", "/v1/chat/completions"]
)
@pytest.mark.parametrize("plan", ["pro", None])
async def test_public_request_plan_is_snapshot_not_current_metadata(async_client, pool, monkeypatch, path, plan):
    from app.modules.claude import transport

    await set_plan(pool, plan)
    install_upstream(monkeypatch)
    original = transport._open_source_stream

    async def send(*args, **kwargs):
        # A background discovery can complete while inference is running.
        await set_plan(pool, "max_20x")
        return await original(*args, **kwargs)

    monkeypatch.setattr(transport, "_open_source_stream", send)
    body = {"model": MODEL, "stream": True}
    if path.endswith("messages"):
        body.update(messages=[{"role": "user", "content": "Hello"}], max_tokens=100)
    elif path.endswith("completions"):
        body.update(messages=[{"role": "user", "content": "Hello"}])
    else:
        body["input"] = "Hello"
    response = await async_client.post(path, json=body, headers=native_headers() if path.endswith("messages") else {})
    assert response.status_code == 200, response.text
    logs = (await async_client.get("/api/request-logs")).json()["requests"]
    row = next(row for row in logs if row["model"] == MODEL)
    assert row["modelSourceKind"] == "claude"
    assert row["planType"] == (plan or "unknown")
    accounts = (await async_client.get("/api/claude-accounts")).json()["accounts"]
    assert all(account["planType"] == "max_20x" for account in accounts)


async def test_failed_and_failover_attempts_use_their_own_plan(async_client, pool, monkeypatch):
    from app.modules.claude import transport
    from app.modules.model_sources.forwarding import ModelSourceForwardingError

    await set_plan(pool, "pro")
    install_upstream(monkeypatch)
    original = transport._open_source_stream
    refused = []

    async def send(source, *args, **kwargs):
        if not refused:
            refused.append(source.id)
            await set_plan(pool, "max_5x")
            raise ModelSourceForwardingError(
                status_code=429, upstream_status_code=429, payload={"error": {"message": "rate limited"}}
            )
        assert source.id != refused[0]
        return await original(source, *args, **kwargs)

    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert response.status_code == 200, response.text
    async with SessionLocal() as session:
        rows = (await session.scalars(select(RequestLog).where(RequestLog.model == MODEL))).all()
        assert {(row.status, row.plan_type) for row in rows} == {("error", "pro"), ("success", "max_5x")}
        assert len({row.model_source_id for row in rows}) == 2
