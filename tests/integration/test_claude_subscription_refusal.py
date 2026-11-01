from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import ClaudeAccount
from app.db.session import SessionLocal
from app.modules.claude.failover import record_oauth_organization_refusal
from app.modules.claude.schemas import AccountState
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration.test_claude_inference import MODEL, install_upstream
from tests.integration.test_claude_routing import choose
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration

REFUSAL = "OAuth authentication is currently not allowed for this organization."


def forbidden(message: str = REFUSAL) -> ModelSourceForwardingError:
    return ModelSourceForwardingError(
        status_code=403,
        upstream_status_code=403,
        payload={"type": "error", "error": {"type": "permission_error", "message": message}},
    )


async def refused_at(source_id: str) -> datetime | None:
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row is not None
        return AccountState.model_validate_json(row.state_json).oauth_refused_at


async def generation(source_id: str) -> int:
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row is not None
        return row.generation


async def test_refusal_blocks_account_and_fails_over(async_client, pool, monkeypatch):
    from app.modules.claude import transport

    captured, _ = install_upstream(monkeypatch)
    original = transport._open_source_stream
    refused: list[str] = []

    async def send(source, route, body, **kwargs):
        if not refused:
            refused.append(source.id)
            raise forbidden()
        return await original(source, route, body, **kwargs)

    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": True})
    assert response.status_code == 200, response.text
    assert len(captured) == 1 and captured[0][0] != refused[0]
    assert await refused_at(refused[0]) is not None
    assert await choose(preferred_source_id=refused[0]) != refused[0]


async def test_refused_pool_reports_refusal_then_fails_locally(async_client, pool, monkeypatch):
    from app.modules.claude import transport

    calls: list[str] = []

    async def send(source, *args, **kwargs):
        calls.append(source.id)
        raise forbidden()

    monkeypatch.setattr(transport, "_open_source_stream", send)
    body = {"model": MODEL, "input": "Hello", "stream": True}
    first = await async_client.post("/v1/responses", json=body)
    assert first.status_code == 403
    assert first.json()["error"]["message"] == REFUSAL
    assert sorted(calls) == sorted(pool)
    second = await async_client.post("/v1/responses", json=body)
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "claude_subscription_inactive"
    assert len(calls) == 2


@pytest.mark.parametrize(
    "message",
    ["Your account does not have permission to use this model.", f"Proxy said: {REFUSAL}"],
)
async def test_other_permission_errors_do_not_block(async_client, pool, monkeypatch, message):
    from app.modules.claude import transport

    calls: list[str] = []

    async def send(source, *args, **kwargs):
        calls.append(source.id)
        raise forbidden(message)

    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": True})
    assert response.status_code == 403
    assert len(calls) == 1
    assert [await refused_at(source_id) for source_id in pool] == [None, None]


async def test_later_metadata_refresh_clears_refusal(async_client, pool):
    await record_oauth_organization_refusal(pool[0], await generation(pool[0]))
    assert await refused_at(pool[0]) is not None
    response = await async_client.post(f"/api/claude-accounts/{pool[0]}/refresh")
    assert response.status_code == 200, response.text
    assert await refused_at(pool[0]) is None
    assert await choose(preferred_source_id=pool[0]) == pool[0]


async def test_refresh_requested_before_refusal_keeps_block(async_client, pool):
    later = datetime.now(UTC) + timedelta(hours=1)
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[0])
        assert row is not None
        state = AccountState.model_validate_json(row.state_json)
        state.oauth_refused_at = later
        row.state_json = state.model_dump_json()
        await session.commit()
    await async_client.post(f"/api/claude-accounts/{pool[0]}/refresh")
    assert await refused_at(pool[0]) == later


async def test_refusal_from_replaced_credential_is_ignored(pool):
    await record_oauth_organization_refusal(pool[0], await generation(pool[0]) - 1)
    assert await refused_at(pool[0]) is None
