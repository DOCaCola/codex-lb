import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import OperationalError

from app.core.utils.time import utcnow
from app.db.models import ClaudeResourceOrigin, ClaudeSessionOwner, ModelSource
from app.db.session import SessionLocal
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import CLI_IDENTITY
from app.modules.claude.resources import ResourceScope, record_origins, resolve_origins, resource_ids, touch_origins
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration.test_claude_inference import MODEL, install_upstream, native_headers, pool

__all__ = ["pool"]
pytestmark = pytest.mark.integration


def blocks(identifier="srv1"):
    return [
        {"type": "server_tool_use", "id": identifier, "name": "web_search", "input": {"query": "hi"}},
        {"type": "web_search_tool_result", "tool_use_id": identifier, "content": []},
    ]


def payload(history=()):
    return {
        "model": MODEL,
        "system": CLI_IDENTITY,
        "max_tokens": 100,
        "stream": True,
        "messages": [{"role": "user", "content": "hi"}, *history],
    }


async def test_native_resource_survives_affinity_expiry_and_rebind(async_client, pool, monkeypatch):
    from app.modules.claude import native

    original_frames = native.native_frames

    async def assert_persisted_before_delivery(body):
        async for frame in original_frames(body):
            for identifier in ("srv1", "srv2"):
                if identifier in frame:
                    scope = ResourceScope("anonymous", "native-thread", MODEL)
                    async with SessionLocal() as session:
                        assert await resolve_origins(session, scope.keys(frozenset({identifier}))) in pool
            yield frame

    monkeypatch.setattr(native, "native_frames", assert_persisted_before_delivery)
    captured, closed = install_upstream(monkeypatch, content=blocks(), stop="pause_turn")
    first = await async_client.post("/v1/messages", headers=native_headers(), json=payload())
    assert "srv1" in first.text
    origin = captured[0][0]
    other = next(source for source in pool if source != origin)
    async with SessionLocal() as session:
        await session.execute(update(ClaudeSessionOwner).values(expires_at=utcnow() - timedelta(hours=2)))
        await session.commit()
    await async_client.patch(f"/api/claude-accounts/{origin}", json={"isEnabled": False})
    captures_b, _ = install_upstream(monkeypatch, content=blocks("srv2"))
    second = await async_client.post("/v1/messages", headers=native_headers(), json=payload())
    assert "srv2" in second.text
    assert captures_b[0][0] == other
    denied = await async_client.post(
        "/v1/messages", headers=native_headers(), json=payload([{"role": "assistant", "content": blocks()}])
    )
    assert denied.status_code == 503 and "owner" in denied.text
    assert len(captures_b) == 1
    await async_client.patch(f"/api/claude-accounts/{origin}", json={"isEnabled": True})
    replay, _ = install_upstream(monkeypatch)
    for identifier, expected in [("srv1", origin), ("srv2", other)]:
        history = [{"role": "assistant", "content": blocks(identifier)}, {"role": "user", "content": "continue"}]
        response = await async_client.post("/v1/messages", headers=native_headers(), json=payload(history))
        assert response.status_code == 200, response.text
        assert replay[-1][0] == expected
        assert replay[-1][2]["messages"] == payload(history)["messages"]
    conflict = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json=payload([{"role": "assistant", "content": blocks("srv1") + blocks("srv2")}]),
    )
    assert conflict.status_code == 400 and "conflicting" in conflict.text
    assert len(replay) == 2
    assert closed == [origin]


async def test_unknown_history_not_blessed_by_affinity(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    await async_client.post("/v1/messages", headers=native_headers(), json=payload())
    for path in ("/v1/messages", "/v1/messages/count_tokens"):
        body = payload([{"role": "assistant", "content": blocks()}])
        if path.endswith("count_tokens"):
            body.pop("stream")
        response = await async_client.post(path, headers=native_headers(), json=body)
        assert response.status_code == 400 and "unknown or expired" in response.text
    assert len(captured) == 1


async def test_commit_failure_never_exposes_resource_or_retries(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch, content=blocks())
    original = SessionLocal.class_.commit

    async def fail_resource_commit(session):
        # Resource upserts are flushed SQL, not session.new ORM objects.
        if await session.scalar(select(ClaudeResourceOrigin.resource_hash).limit(1)):
            raise OperationalError("commit", {}, RuntimeError("database unavailable"))
        await original(session)

    monkeypatch.setattr(SessionLocal.class_, "commit", fail_resource_commit)
    response = await async_client.post("/v1/messages", headers=native_headers(), json=payload())
    assert "srv1" not in response.text
    assert "response stopped" in response.text
    assert len(captured) == len(closed) == 1
    async with SessionLocal() as session:
        assert await session.scalar(select(ClaudeResourceOrigin.resource_hash)) is None


async def test_scope_expiry_conflict_touch_and_deletion(pool):
    scope = ResourceScope("key", "thread", MODEL)
    value = {"content": blocks()}
    keys = scope.keys(resource_ids(value))
    await record_origins(scope, pool[0], value)
    await record_origins(scope, pool[0], value)
    with pytest.raises(ModelSourceForwardingError):
        await record_origins(scope, pool[1], value)
    async with SessionLocal() as session:
        assert await resolve_origins(session, keys) == pool[0]
        for alternate in (
            ResourceScope("other", "thread", MODEL),
            ResourceScope("key", "other", MODEL),
            ResourceScope("key", "thread", "anthropic/claude-sonnet-5"),
        ):
            with pytest.raises(ClaudeError, match="unknown or expired"):
                await resolve_origins(session, alternate.keys(resource_ids(value)))
        await session.execute(update(ClaudeResourceOrigin).values(expires_at=utcnow() + timedelta(hours=1)))
        await session.commit()
    await touch_origins(keys, pool[0])
    async with SessionLocal() as session:
        row = await session.get(ClaudeResourceOrigin, keys[0])
        assert row.expires_at > utcnow() + timedelta(days=29)
        await session.execute(delete(ModelSource).where(ModelSource.id == pool[0]))
        await session.commit()
    async with SessionLocal() as session:
        with pytest.raises(ClaudeError, match="unknown or expired"):
            await resolve_origins(session, keys)


async def test_expired_origin_cannot_be_revived_by_replay(pool):
    scope = ResourceScope("key", "thread", MODEL)
    await record_origins(scope, pool[0], {"content": blocks()})
    keys = scope.keys(frozenset({"srv1"}))
    async with SessionLocal() as session:
        await session.execute(update(ClaudeResourceOrigin).values(expires_at=utcnow() - timedelta(seconds=1)))
        await session.commit()
    with pytest.raises(ClaudeError, match="expired"):
        await touch_origins(keys, pool[0])
    async with SessionLocal() as session:
        with pytest.raises(ClaudeError, match="expired"):
            await resolve_origins(session, keys)


async def test_concurrent_registration_never_overwrites_origin(pool):
    scope = ResourceScope("key", "thread", MODEL)
    value = {"content": blocks()}
    outcomes = await asyncio.gather(
        record_origins(scope, pool[0], value), record_origins(scope, pool[1], value), return_exceptions=True
    )
    assert sum(result is None for result in outcomes) == 1
    assert sum(isinstance(result, ModelSourceForwardingError) for result in outcomes) == 1
    winner = pool[outcomes.index(None)]
    await asyncio.gather(record_origins(scope, winner, value), record_origins(scope, winner, value))
    async with SessionLocal() as session:
        assert await resolve_origins(session, scope.keys(resource_ids(value))) == winner


@pytest.mark.parametrize("fail_commit", [False, True])
async def test_native_json_and_count_tokens_provenance(async_client, pool, monkeypatch, fail_commit):
    from app.modules.claude import transport

    calls = []

    @asynccontextmanager
    async def post(url, **kwargs):
        calls.append(url)
        data = (
            {"input_tokens": 1}
            if "count_tokens" in url
            else {
                "id": "msg1",
                "content": blocks(),
                "stop_reason": "pause_turn",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        )
        yield SimpleNamespace(status=200, headers={}, json=AsyncMock(return_value=data))

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(post=post)

    monkeypatch.setattr(transport, "lease_model_source_session", lease)
    original = SessionLocal.class_.commit

    async def commit(session):
        if fail_commit and await session.scalar(select(ClaudeResourceOrigin.resource_hash).limit(1)):
            raise OperationalError("commit", {}, RuntimeError("unavailable"))
        await original(session)

    monkeypatch.setattr(SessionLocal.class_, "commit", commit)
    body = {**payload(), "stream": False}
    response = await async_client.post("/v1/messages", headers=native_headers(), json=body)
    assert len(calls) == 1
    if fail_commit:
        assert response.status_code == 502 and "srv1" not in response.text
        return
    assert response.status_code == 200 and response.json()["content"] == blocks()
    async with SessionLocal() as session:
        row = await session.scalar(select(ClaudeResourceOrigin))
        assert row is not None
        expiry = row.expires_at
    body["messages"].append({"role": "assistant", "content": blocks()})
    body.pop("stream")
    counted = await async_client.post("/v1/messages/count_tokens", headers=native_headers(), json=body)
    assert counted.status_code == 200, counted.text
    async with SessionLocal() as session:
        assert (await session.scalar(select(ClaudeResourceOrigin))).expires_at == expiry
