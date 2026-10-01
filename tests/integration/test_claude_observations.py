import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, update

from app.db.models import ClaudeAccount, ClaudeQuotaHistory
from app.db.session import SessionLocal
from app.modules.claude import transport
from app.modules.claude.client import ClaudeClient
from app.modules.claude.observations import record_headers
from app.modules.claude.quota import quota_status
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import AccountState, ClaudeUpdate, QuotaWindow, UsageSnapshot
from app.modules.claude.service import ClaudeService
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration.test_claude_inference import MODEL, install_upstream
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration


def headers(value):
    return {"anthropic-ratelimit-unified-5h-utilization": str(value)}


async def snapshot(source_id):
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        return row.generation, AccountState.model_validate_json(row.state_json)


@pytest.mark.parametrize("path", ["/v1/messages", "/v1/responses", "/backend-api/codex/responses"])
async def test_each_physical_response_is_attributed(async_client, pool, monkeypatch, path):
    captured, closed = install_upstream(monkeypatch)
    original = transport._open_source_stream
    refused = []

    async def send(source, *args, **kwargs):
        if not refused:
            refused.append(source.id)
            raise ModelSourceForwardingError(
                status_code=429,
                upstream_status_code=429,
                payload={"error": {"message": "limited"}},
                upstream_headers=headers(0.95),
            )
        stack, response, extra = await original(source, *args, **kwargs)
        response.headers.update(headers(0.25))
        return stack, response, extra

    monkeypatch.setattr(transport, "_open_source_stream", send)
    body = {"model": MODEL, "stream": True}
    body.update(
        {"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 100}
        if path.endswith("messages")
        else {"input": "Hi"}
    )
    response = await async_client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert len(captured) == len(closed) == 1
    _, failed = await snapshot(refused[0])
    _, success = await snapshot(captured[0][0])
    assert failed.header_usage["five_hour"].window.utilization == 95
    assert success.header_usage["five_hour"].window.utilization == 25
    assert refused[0] != captured[0][0]


async def test_generation_ordering_and_history_throttle(pool):
    source_id = pool[0]
    generation, initial = await snapshot(source_id)
    now = datetime.now(UTC)
    await record_headers(source_id, generation, headers(0.7), requested_at=now)
    await record_headers(source_id, generation, headers(0.2), requested_at=now - timedelta(seconds=1))
    await record_headers(source_id, generation, headers(0.8), requested_at=now + timedelta(microseconds=1))
    await record_headers(source_id, generation, headers(0.8), requested_at=now + timedelta(microseconds=2))
    _, state = await snapshot(source_id)
    assert state.header_usage["five_hour"].window.utilization == 80
    assert state.usage_updated_at == initial.usage_updated_at
    async with SessionLocal() as session:
        samples = await session.scalars(
            select(ClaudeQuotaHistory.used_percent)
            .where(ClaudeQuotaHistory.source_id == source_id, ClaudeQuotaHistory.window == "five_hour")
            .order_by(ClaudeQuotaHistory.observed_at)
        )
        # The out-of-order reading is ignored; the moved reading is new evidence; the repeat is throttled.
        assert list(samples) == [70, 80]
        await session.execute(
            update(ClaudeAccount).where(ClaudeAccount.source_id == source_id).values(generation=generation + 1)
        )
        await session.commit()
    await record_headers(source_id, generation, headers(0.1), requested_at=now + timedelta(seconds=2))
    _, state = await snapshot(source_id)
    assert state.header_usage["five_hour"].window.utilization == 80


async def test_delayed_poll_preserves_headers_and_concurrent_settings(pool):
    source_id = pool[0]
    generation, _ = await snapshot(source_id)
    started = asyncio.Event()
    proceed = asyncio.Event()
    now = datetime.now(UTC)

    async def usage(*args):
        started.set()
        await proceed.wait()
        return UsageSnapshot(five_hour=QuotaWindow(utilization=10))

    async def poll():
        async with SessionLocal() as session:
            client = ClaudeClient()
            client.usage = usage
            return await ClaudeService(ClaudeRepository(session), client).refresh(source_id, catalog=False)

    task = asyncio.create_task(poll())
    try:
        await asyncio.wait_for(started.wait(), 5)
        await record_headers(source_id, generation, headers(0.6), requested_at=datetime.now(UTC))
        async with SessionLocal() as session:
            await ClaudeService(ClaudeRepository(session)).update(source_id, ClaudeUpdate(selections=[]))
        proceed.set()
        await task
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    _, state = await snapshot(source_id)
    assert state.selections == []
    assert state.usage_updated_at >= now
    assert quota_status(state, now=datetime.now(UTC)).windows[0].utilization == 60


async def test_observation_failure_does_not_break_stream(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch)
    original = transport._open_source_stream

    async def send(*args, **kwargs):
        stack, response, extra = await original(*args, **kwargs)
        response.headers.update(headers(0.2))
        return stack, response, extra

    monkeypatch.setattr(transport, "_open_source_stream", send)
    monkeypatch.setattr(ClaudeRepository, "mutate_state", AsyncMock(side_effect=RuntimeError("private detail")))
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert response.status_code == 200 and "Hello from Claude" in response.text
    assert len(captured) == len(closed) == 1


async def test_observation_database_timeout_is_bounded(pool, monkeypatch):
    generation, _ = await snapshot(pool[0])
    cancelled = asyncio.Event()

    async def stalled(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(ClaudeRepository, "mutate_state", stalled)
    await asyncio.wait_for(record_headers(pool[0], generation, headers(0.5), requested_at=datetime.now(UTC)), 2)
    assert cancelled.is_set()


@pytest.mark.parametrize("count_tokens", [False, True])
async def test_native_json_observes_before_body(async_client, pool, monkeypatch, count_tokens):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    observed = []
    original = transport.record_headers

    async def observe(source_id, *args, **kwargs):
        await original(source_id, *args, **kwargs)
        observed.append(source_id)

    async def body(*, content_type=None):
        assert len(observed) == 1
        return (
            {"input_tokens": 10}
            if count_tokens
            else {
                "id": "msg_done",
                "content": [{"type": "text", "text": "done"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 1},
            }
        )

    @asynccontextmanager
    async def post(*args, **kwargs):
        yield SimpleNamespace(status=200, headers=headers(0.35), json=body)

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(post=post)

    monkeypatch.setattr(transport, "lease_model_source_session", lease)
    monkeypatch.setattr(transport, "record_headers", observe)
    payload = {"model": MODEL, "messages": [{"role": "user", "content": "Hi"}]}
    if not count_tokens:
        payload["max_tokens"] = 100
    result = await async_client.post("/v1/messages/count_tokens" if count_tokens else "/v1/messages", json=payload)
    assert result.status_code == 200, result.text
    _, state = await snapshot(observed[0])
    assert state.header_usage["five_hour"].window.utilization == 35


async def test_cancel_observation_closes_stream(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch)
    monkeypatch.setattr(transport, "record_headers", AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert len(captured) == len(closed) == 1


async def test_deleted_source_is_not_recreated(async_client, pool):
    generation, _ = await snapshot(pool[0])
    result = await async_client.delete(f"/api/claude-accounts/{pool[0]}")
    assert result.status_code in (200, 204)
    await record_headers(pool[0], generation, headers(0.5), requested_at=datetime.now(UTC))
    async with SessionLocal() as session:
        assert await session.get(ClaudeAccount, pool[0]) is None


async def test_overshoot_is_persisted_and_exposed_as_exhausted(async_client, pool):
    generation, _ = await snapshot(pool[0])
    await record_headers(pool[0], generation, headers(1.04), requested_at=datetime.now(UTC))
    _, state = await snapshot(pool[0])
    assert state.header_usage["five_hour"].window.utilization == 104
    quota = quota_status(state, now=datetime.now(UTC))
    assert quota.windows[0].exhausted
    assert all(model.blocked for model in quota.models)
    response = await async_client.get("/api/claude-accounts")
    assert response.status_code == 200
    account = next(item for item in response.json()["accounts"] if item["id"] == pool[0])
    window = account["quota"]["windows"][0]
    assert window["utilization"] == 104
    assert window["exhausted"] is True
    assert window["provenance"] == "inference_header"
    async with SessionLocal() as session:
        sample = await session.scalar(
            select(ClaudeQuotaHistory.used_percent).where(
                ClaudeQuotaHistory.source_id == pool[0], ClaudeQuotaHistory.window == "five_hour"
            )
        )
        assert sample == 104
