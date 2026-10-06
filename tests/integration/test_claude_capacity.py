import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.db.models import ClaudeCooldown
from app.db.session import SessionLocal
from app.modules.claude.client import ClaudeClient
from app.modules.proxy import api, source_admission
from tests.integration.test_claude_inference import MODEL, install_upstream
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration


@pytest.fixture
def bulkhead(monkeypatch):
    value = source_admission.SourceBulkhead()
    monkeypatch.setattr(source_admission, "_BULKHEAD", value)
    return value


async def configure(async_client, pool):
    for source_id in pool:
        response = await async_client.patch(f"/api/claude-accounts/{source_id}", json={"maxConcurrency": 1})
        assert response.status_code == 200, response.text
        assert response.json()["maxConcurrency"] == 1


@pytest.mark.parametrize("path", ["/v1/messages", "/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("all_full", [False, True])
async def test_atomic_rejection_reselects_without_send(async_client, pool, monkeypatch, bulkhead, path, all_full):
    await configure(async_client, pool)
    captured, closed = install_upstream(monkeypatch)
    refresh = AsyncMock(side_effect=AssertionError("capacity must not force refresh"))
    monkeypatch.setattr(ClaudeClient, "refresh", refresh)
    reserve = AsyncMock(wraps=api._enforce_request_limits)
    monkeypatch.setattr(api, "_enforce_request_limits", reserve)
    original = api.try_claim_source_admission
    attempts, held = [], []

    def claim(source):
        attempts.append(source.id)
        if len(attempts) == 1 or all_full:
            held.append(bulkhead.try_acquire(source.id, 1))
        return original(source)

    monkeypatch.setattr(api, "try_claim_source_admission", claim)
    body = {"model": MODEL, "stream": True}
    body.update(
        {"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 100}
        if path.endswith("messages")
        else {"input": "Hi"}
    )
    response = await async_client.post(path, json=body)
    assert len(attempts) == 2 and len(set(attempts)) == 2
    assert len(captured) == len(closed) == (0 if all_full else 1)
    assert reserve.await_count == (0 if all_full else 1)
    if all_full:
        assert response.status_code == 503
        assert response.headers["retry-after"] == "1"
        assert response.json()["error"]["code"] == "model_source_busy"
    else:
        assert response.status_code == 200, response.text
        assert captured[0][0] == attempts[1]
        assert bulkhead.in_flight(attempts[1]) == 0
    refresh.assert_not_called()
    async with SessionLocal() as session:
        assert list(await session.scalars(select(ClaudeCooldown))) == []
    for slot in held:
        bulkhead.release(slot)
    assert all(bulkhead.in_flight(source_id) == 0 for source_id in pool)


@pytest.mark.parametrize("search", [False, True])
async def test_owned_history_cannot_escape_capacity(async_client, pool, monkeypatch, bulkhead, search):
    from tests.unit.test_claude_search import search_content

    await configure(async_client, pool)
    captured, _ = install_upstream(
        monkeypatch,
        content=search_content()
        if search
        else [
            {"type": "thinking", "thinking": "reason", "signature": "signed"},
            {"type": "text", "text": "answer"},
        ],
    )
    headers = {"session_id": "capacity-owner"}
    body = {"model": MODEL, "input": "Hello", "stream": False}
    if search:
        body["tools"] = [{"type": "web_search"}]
    first = await async_client.post("/v1/responses", headers=headers, json=body)
    assert first.status_code == 200, first.text
    slot = bulkhead.try_acquire(captured[0][0], 1)
    body["input"] = first.json()["output"]
    result = await async_client.post("/v1/responses", headers=headers, json=body)
    assert result.status_code == 503, result.text
    assert result.json()["error"]["code"] == "model_source_busy"
    assert len(captured) == 1
    bulkhead.release(slot)


async def test_settings_clear_and_validation(async_client, pool):
    await configure(async_client, pool)
    path = f"/api/claude-accounts/{pool[0]}"
    response = await async_client.patch(path, json={"name": "renamed"})
    assert response.json()["maxConcurrency"] == 1
    for invalid in (0, -1, True, 1.5, "2"):
        response = await async_client.patch(path, json={"maxConcurrency": invalid})
        assert response.status_code == 422
    response = await async_client.patch(path, json={"maxConcurrency": None})
    assert response.status_code == 200
    assert response.json()["maxConcurrency"] is None


async def test_cancel_during_affinity_commit_releases_slot(async_client, pool, monkeypatch, bulkhead):
    from app.modules.claude.session import NativeSessionBinding

    await configure(async_client, pool)
    captured, _ = install_upstream(monkeypatch)
    monkeypatch.setattr(NativeSessionBinding, "commit", AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await async_client.post(
            "/v1/messages",
            json={
                "model": MODEL,
                "max_tokens": 100,
                "stream": True,
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )
    assert not captured
    assert all(bulkhead.in_flight(source_id) == 0 for source_id in pool)


@pytest.mark.parametrize("path", ["/v1/messages", "/v1/responses"])
async def test_admission_recency_failure_releases_owned_slot(async_client, pool, monkeypatch, bulkhead, path):
    from app.modules.claude import session as claude_session

    await configure(async_client, pool)
    captured, _ = install_upstream(monkeypatch)
    monkeypatch.setattr(claude_session, "record_admission", AsyncMock(side_effect=asyncio.CancelledError))
    body = {"model": MODEL, "stream": True}
    body.update(
        {"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 100}
        if path.endswith("messages")
        else {"input": "Hi"}
    )
    with pytest.raises(asyncio.CancelledError):
        await async_client.post(path, json=body)
    assert not captured
    assert all(bulkhead.in_flight(source_id) == 0 for source_id in pool)


async def test_auth_retry_does_not_move_when_owner_fills(async_client, pool, monkeypatch, bulkhead):
    from app.modules.claude import transport
    from app.modules.model_sources.forwarding import ModelSourceForwardingError
    from tests.integration.test_claude_auth_recovery import rotated

    await configure(async_client, pool)
    monkeypatch.setattr(ClaudeClient, "refresh", AsyncMock(side_effect=rotated))
    sent, held = [], []

    async def send(source, *args, **kwargs):
        sent.append(source.id)
        # Simulate a different request filling the account after this send.
        held.append(bulkhead.try_acquire(source.id, None))
        raise ModelSourceForwardingError(
            status_code=401, upstream_status_code=401, payload={"error": {"type": "authentication_error"}}
        )

    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "model_source_busy"
    assert len(sent) == 1
    for slot in held:
        bulkhead.release(slot)


async def test_rejected_new_candidate_does_not_bind_session(async_client, pool, monkeypatch, bulkhead):
    from app.modules.claude.session import NativeSessionOwnership

    await configure(async_client, pool)
    captured, _ = install_upstream(monkeypatch)
    held = [bulkhead.try_acquire(source_id, 1) for source_id in pool]
    response = await async_client.post(
        "/v1/messages",
        headers={"x-claude-code-session-id": "capacity-session"},
        json={
            "model": MODEL,
            "max_tokens": 100,
            "stream": True,
            "messages": [{"role": "user", "content": "Hi"}],
        },
    )
    assert response.status_code == 503
    assert not captured
    async with SessionLocal() as session:
        assert (
            await NativeSessionOwnership(
                session, client_scope="anonymous", conversation_id="capacity-session", model=MODEL
            ).owner()
            is None
        )
    for slot in held:
        bulkhead.release(slot)


async def test_concurrent_binding_change_releases_admission(async_client, pool, monkeypatch, bulkhead):
    from app.modules.claude.session import NativeSessionBinding, NativeSessionOwnership

    await configure(async_client, pool)
    captured, _ = install_upstream(monkeypatch)
    commit = NativeSessionBinding.commit

    async def change_owner(self, source_id):
        async with SessionLocal() as session:
            await NativeSessionOwnership(
                session, client_scope=self.client_scope, conversation_id=self.conversation_id, model=self.model
            ).claim(next(value for value in pool if value != source_id))
        await commit(self, source_id)

    monkeypatch.setattr(NativeSessionBinding, "commit", change_owner)
    response = await async_client.post(
        "/v1/messages",
        json={
            "model": MODEL,
            "max_tokens": 100,
            "stream": True,
            "messages": [{"role": "user", "content": "Hi"}],
        },
    )
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "claude_session_changed"
    assert not captured
    assert all(bulkhead.in_flight(source_id) == 0 for source_id in pool)
