from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.models import ClaudeCooldown
from app.db.session import SessionLocal
from app.modules.claude.failover import Refusal, record_refusals
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.claude_quota_helpers import overage_headers
from tests.integration.test_claude_inference import MODEL, install_upstream
from tests.integration.test_claude_routing import choose
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "path,stream",
    [
        ("/v1/messages", True),
        ("/v1/responses", True),
        ("/backend-api/codex/responses", True),
        ("/v1/responses", False),
        ("/backend-api/codex/responses", False),
    ],
)
@pytest.mark.parametrize("quota_kind", ["generic", "overage", "mixed"])
async def test_retry_rebuilds_account_identity_after_settlement(
    async_client, pool, monkeypatch, path, stream, quota_kind
):
    from app.modules.claude import transport
    from app.modules.proxy.source_dispatch import SourceDispatch

    captured, closed = install_upstream(monkeypatch)
    original = transport._open_source_stream
    finish = SourceDispatch.finish_with_forwarding_error
    failed, settled = [], []

    async def settle(self, error):
        await finish(self, error)
        assert self.finished and self._claims_released and self._reservation_done
        settled.append(self.source.id)

    async def send(source, route, body, **kwargs):
        if not failed:
            failed.append((source.id, kwargs["prepared_headers"]))
            raise ModelSourceForwardingError(
                status_code=429,
                upstream_status_code=429,
                payload={"error": {"message": "limited"}},
                retry_after="120",
                upstream_headers=overage_headers(mixed=quota_kind == "mixed") if quota_kind != "generic" else {},
            )
        assert settled == [failed[0][0]]
        return await original(source, route, body, **kwargs)

    monkeypatch.setattr(SourceDispatch, "finish_with_forwarding_error", settle)
    monkeypatch.setattr(transport, "_open_source_stream", send)
    body = {"model": MODEL, "stream": stream}
    body.update(
        {"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 100}
        if path.endswith("messages")
        else {"input": "Hello"}
    )
    response = await async_client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert len(captured) == 1
    assert closed == [captured[0][0]]
    assert captured[0][0] != failed[0][0]
    assert captured[0][3]["authorization"] != failed[0][1]["authorization"]
    async with SessionLocal() as session:
        cooldown = await session.get(ClaudeCooldown, (failed[0][0], MODEL))
        assert cooldown is not None
        account_cooldown = await session.get(ClaudeCooldown, (failed[0][0], "*"))
        assert (account_cooldown is not None) == (quota_kind == "mixed")
    if quota_kind == "overage":
        assert await choose(model="anthropic/claude-sonnet-5", preferred_source_id=failed[0][0]) == failed[0][0]
    elif quota_kind == "mixed":
        assert await choose(model="anthropic/claude-sonnet-5", preferred_source_id=failed[0][0]) != failed[0][0]
        later = datetime.now(UTC) + timedelta(hours=3)
        assert (
            await choose(model="anthropic/claude-sonnet-5", preferred_source_id=failed[0][0], now=later) == failed[0][0]
        )
        assert await choose(preferred_source_id=failed[0][0], now=later) != failed[0][0]


async def test_entitlement_preserves_pool(async_client, pool, monkeypatch):
    from app.modules.claude import transport

    calls = []

    async def send(source, *args, **kwargs):
        calls.append(source.id)
        raise ModelSourceForwardingError(
            status_code=429,
            upstream_status_code=429,
            payload={"error": {"message": "Usage credits are required for fast mode."}},
        )

    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": True})
    assert response.status_code == 429
    assert len(calls) == 1
    async with SessionLocal() as session:
        assert list(await session.scalars(select(ClaudeCooldown))) == []


async def test_cooldown_scope_monotonic_and_persistent(pool):
    now = datetime.now(UTC)
    await record_refusals(pool[0], MODEL, (Refusal("model", now + timedelta(hours=1), "retry_after"),))
    await record_refusals(pool[0], MODEL, (Refusal("model", now + timedelta(seconds=5), "retry_after"),))
    assert await choose(preferred_source_id=pool[0]) == pool[1]
    assert await choose(model="anthropic/claude-sonnet-5", preferred_source_id=pool[0]) == pool[0]
    async with SessionLocal() as session:
        row = await session.get(ClaudeCooldown, (pool[0], MODEL))
        assert row.until.replace(tzinfo=UTC) == now + timedelta(hours=1)
    await record_refusals(pool[0], MODEL, (Refusal("account", now + timedelta(hours=1), "reset"),))
    assert await choose(model="anthropic/claude-sonnet-5", preferred_source_id=pool[0]) == pool[1]


async def test_mixed_restrictions_are_atomic(pool, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    execute = AsyncSession.execute
    writes = 0

    async def fail_second_write(self, statement, *args, **kwargs):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise RuntimeError("simulated persistence failure")
        return await execute(self, statement, *args, **kwargs)

    now = datetime.now(UTC)
    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "execute", fail_second_write)
        with pytest.raises(RuntimeError, match="simulated persistence failure"):
            await record_refusals(
                pool[0],
                MODEL,
                (
                    Refusal("account", now + timedelta(hours=2), "reset"),
                    Refusal("model", now + timedelta(hours=80), "reset"),
                ),
            )
    async with SessionLocal() as session:
        assert list(await session.scalars(select(ClaudeCooldown))) == []


@pytest.mark.parametrize("count_tokens", [False, True])
@pytest.mark.parametrize("status", [401, 429, 529])
async def test_native_json_reprepares_and_closes(async_client, pool, monkeypatch, count_tokens, status):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.modules.claude import transport
    from app.modules.claude.client import ClaudeClient
    from tests.integration.test_claude_auth_recovery import rotated

    monkeypatch.setattr(ClaudeClient, "refresh", AsyncMock(side_effect=rotated))
    sent, closed = [], []

    @asynccontextmanager
    async def post(url, **kwargs):
        sent.append(kwargs["headers"]["authorization"])
        failed = len(sent) == 1
        data = (
            {"error": {"message": "limited"}}
            if failed
            else {"input_tokens": 10}
            if count_tokens
            else {
                "id": "msg_done",
                "content": [{"type": "text", "text": "done"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 1},
            }
        )
        try:
            yield SimpleNamespace(
                status=status if failed else 200,
                headers=overage_headers() if status == 429 else {"Retry-After": "0" if status == 529 else "120"},
                json=AsyncMock(return_value=data),
            )
        finally:
            closed.append(True)

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(post=post)

    monkeypatch.setattr(transport, "lease_model_source_session", lease)
    body = {"model": MODEL, "messages": [{"role": "user", "content": "Hi"}]}
    if not count_tokens:
        body["max_tokens"] = 100
    response = await async_client.post("/v1/messages/count_tokens" if count_tokens else "/v1/messages", json=body)
    assert response.status_code == 200, response.text
    assert len(sent) == len(closed) == 2
    assert (sent[0] == sent[1]) == (status == 529)
    if status == 429:
        async with SessionLocal() as session:
            rows = list(await session.scalars(select(ClaudeCooldown)))
            assert len(rows) == 1 and rows[0].model == MODEL
            source_id = rows[0].source_id
        assert await choose(model="anthropic/claude-sonnet-5", preferred_source_id=source_id) == source_id


@pytest.mark.parametrize("status", [429, 529])
async def test_signature_and_account_recovery_share_budget(async_client, pool, monkeypatch, status):
    from app.modules.claude import transport
    from tests.integration.test_claude_accounts import import_body

    third = await async_client.post("/api/claude-accounts/import", json=import_body(refresh="account-c"))
    third_id = third.json()["id"]
    await async_client.post(f"/api/claude-accounts/{third_id}/refresh")
    await async_client.patch(f"/api/claude-accounts/{third_id}", json={"selections": [{"model": "claude-opus-5"}]})

    sent = []

    async def send(source, *args, **kwargs):
        sent.append(source.id)
        signature = len(sent) % 2 == 1
        raise ModelSourceForwardingError(
            status_code=400 if signature else status,
            upstream_status_code=400 if signature else status,
            payload={"error": {"message": "Invalid signature in thinking block" if signature else "limited"}},
        )

    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post(
        "/v1/messages",
        json={
            "model": MODEL,
            "stream": True,
            "max_tokens": 100,
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "old", "signature": "sig"},
                        {"type": "text", "text": "answer"},
                    ],
                },
                {"role": "user", "content": "Continue"},
            ],
        },
    )
    assert response.status_code == status, response.text
    assert len(sent) == 4
    assert sent[0] == sent[1] and sent[2] == sent[3]
    assert (sent[0] == sent[2]) == (status == 529)


async def test_disconnect_between_attempts_stops_recovery(async_client, pool, monkeypatch):
    from starlette.requests import Request

    from app.modules.claude import failover, transport

    disconnected = False
    sent = []
    record = failover.record_refusals

    async def record_then_disconnect(*args):
        nonlocal disconnected
        await record(*args)
        disconnected = True

    async def is_disconnected(self):
        return disconnected

    async def send(source, *args, **kwargs):
        sent.append(source.id)
        raise ModelSourceForwardingError(
            status_code=429, upstream_status_code=429, payload={"error": {"message": "limited"}}
        )

    monkeypatch.setattr(failover, "record_refusals", record_then_disconnect)
    monkeypatch.setattr(Request, "is_disconnected", is_disconnected)
    monkeypatch.setattr(transport, "_open_source_stream", send)
    await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert len(sent) == 1


@pytest.mark.parametrize("search", [False, True])
@pytest.mark.parametrize("status", [401, 429])
async def test_bound_history_preserves_original_refusal(async_client, pool, monkeypatch, search, status):
    from unittest.mock import AsyncMock

    from app.modules.claude import transport
    from app.modules.claude.client import ClaudeClient
    from tests.integration.test_claude_auth_recovery import rotated
    from tests.unit.test_claude_search import search_content

    monkeypatch.setattr(ClaudeClient, "refresh", AsyncMock(side_effect=rotated))

    captured, _ = install_upstream(
        monkeypatch,
        content=search_content()
        if search
        else [
            {"type": "thinking", "thinking": "reason", "signature": "signed"},
            {"type": "text", "text": "answer"},
        ],
    )
    headers = {"session_id": "strict-failover"}
    first_body = {"model": MODEL, "input": "Hello", "stream": False}
    if search:
        first_body["tools"] = [{"type": "web_search"}]
    first = await async_client.post("/v1/responses", headers=headers, json=first_body)
    assert first.status_code == 200, first.text
    sent = []

    async def refuse(source, *args, **kwargs):
        sent.append(source.id)
        raise ModelSourceForwardingError(
            status_code=status,
            upstream_status_code=status,
            payload={"error": {"message": "original quota refusal"}},
            retry_after="123",
        )

    monkeypatch.setattr(transport, "_open_source_stream", refuse)
    body = {"model": MODEL, "input": first.json()["output"], "stream": True}
    if search:
        body["tools"] = [{"type": "web_search"}]
        body["input"].append({"role": "user", "content": "continue"})
    result = await async_client.post("/v1/responses", headers=headers, json=body)
    assert result.status_code == status, result.text
    assert result.headers["retry-after"] == "123"
    assert "original quota refusal" in result.text
    assert sent == [captured[0][0]] * (2 if status == 401 else 1)


async def test_late_stream_error_never_rotates(async_client, pool, monkeypatch):
    from app.modules.claude import transport

    captured, closed = install_upstream(monkeypatch)
    events = transport._iter_sse_events

    async def late_error(*args):
        async for event in events(*args):
            yield event
            if "content_block_start" not in event:
                continue
            raise ModelSourceForwardingError(
                status_code=429, upstream_status_code=429, payload={"error": {"message": "late refusal"}}
            )

    monkeypatch.setattr(transport, "_iter_sse_events", late_error)
    await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": False})
    assert len(captured) == len(closed) == 1
    async with SessionLocal() as session:
        assert list(await session.scalars(select(ClaudeCooldown))) == []
