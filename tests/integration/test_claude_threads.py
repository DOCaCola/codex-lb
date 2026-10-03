from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import OperationalError

from app.core.utils.time import utcnow
from app.db.models import ClaudeResourceOrigin, ClaudeSessionOwner
from app.db.session import SessionLocal
from app.modules.claude.profile import CLI_IDENTITY
from app.modules.claude.resources import ResourceScope, resolve_origins
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration.test_claude_inference import MODEL, install_upstream, native_headers, pool

__all__ = ["pool"]
pytestmark = pytest.mark.integration


def payload(operation="create", *, stream=True, previous="msg_fixture"):
    thread = {"type": operation}
    if operation == "continue":
        thread["previous_message_id"] = previous
    return {
        "model": MODEL,
        "system": CLI_IDENTITY,
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 100,
        "stream": stream,
        "thread": thread,
    }


@pytest.mark.parametrize("stream", [False, True])
async def test_thread_message_binds_account_before_publication_and_survives_affinity_expiry(
    async_client, pool, monkeypatch, stream
):
    from app.modules.claude import native, transport

    captured, _ = install_upstream(monkeypatch)
    if not stream:

        @asynccontextmanager
        async def lease():
            class Response:
                status = 200
                headers = {}

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_):
                    pass

                async def json(self, **_kwargs):
                    return {
                        "id": "msg_fixture",
                        "type": "message",
                        "content": [{"type": "text", "text": "hello"}],
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 10, "output_tokens": 2},
                    }

            def post(_url, **kwargs):
                captured.append((kwargs["headers"]["authorization"], kwargs["json"]))
                return Response()

            yield SimpleNamespace(post=post)

        monkeypatch.setattr(transport, "lease_model_source_session", lease)
    else:
        original = native.native_frames

        async def frames(body):
            async for frame in original(body):
                if "msg_fixture" in frame:
                    async with SessionLocal() as session:
                        keys = ResourceScope("anonymous", MODEL).keys(frozenset({"msg_fixture"}), kind="message_thread")
                        assert await resolve_origins(session, keys) in pool
                yield frame

        monkeypatch.setattr(native, "native_frames", frames)
    response = await async_client.post("/v1/messages", headers=native_headers(), json=payload(stream=stream))
    assert response.status_code == 200, response.text
    origin = captured[0][0]
    async with SessionLocal() as session:
        await session.execute(delete(ClaudeSessionOwner))
        await session.commit()
    response = await async_client.post(
        "/v1/messages", headers=native_headers(), json=payload("continue", stream=stream)
    )
    assert response.status_code == 200, response.text
    assert captured[-1][0] == origin
    assert len(captured) == 2
    wire = captured[-1][2] if stream else captured[-1][1]
    assert wire["thread"] == {"type": "continue", "previous_message_id": "msg_fixture"}


async def test_missing_thread_provenance_returns_replayable_404_without_dispatch(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post("/v1/messages", headers=native_headers(), json=payload("continue"))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "thread_not_found"
    assert "thread_not_found" in response.json()["error"]["message"]
    assert not captured


async def test_thread_provenance_is_scoped_to_authenticated_client(async_client, pool, monkeypatch):
    from tests.integration.model_source_helpers import _enable_api_key_auth

    await _enable_api_key_auth(async_client)
    headers = []
    for name in ("thread-owner", "other-client"):
        response = await async_client.post("/api/api-keys/", json={"name": name, "assignedSourceIds": list(pool)})
        assert response.status_code == 200, response.text
        headers.append({**native_headers(), "Authorization": f"Bearer {response.json()['key']}"})
    captured, _ = install_upstream(monkeypatch)
    assert (await async_client.post("/v1/messages", headers=headers[0], json=payload())).status_code == 200
    response = await async_client.post("/v1/messages", headers=headers[1], json=payload("continue"))
    assert response.status_code == 404, response.text
    assert len(captured) == 1
    assert (await async_client.post("/v1/messages", headers=headers[0], json=payload("continue"))).status_code == 200
    assert captured[-1][0] == captured[0][0]


async def test_failed_thread_persistence_never_publishes_message_id(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch)
    original = SessionLocal.class_.commit

    async def fail_origin_commit(session):
        if await session.scalar(select(ClaudeResourceOrigin.resource_hash).limit(1)):
            raise OperationalError("commit", {}, RuntimeError("database unavailable"))
        await original(session)

    monkeypatch.setattr(SessionLocal.class_, "commit", fail_origin_commit)
    response = await async_client.post("/v1/messages", headers=native_headers(), json=payload())
    assert "msg_fixture" not in response.text
    assert "response stopped" in response.text
    assert len(captured) == len(closed) == 1


@pytest.mark.parametrize("thread", [None, {}, {"type": "unknown"}, {"type": "continue"}])
async def test_invalid_thread_is_rejected_before_upstream(async_client, pool, monkeypatch, thread):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post("/v1/messages", headers=native_headers(), json={**payload(), "thread": thread})
    assert response.status_code == 400, response.text
    assert not captured


async def test_expired_thread_and_other_model_are_not_reused(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    assert (await async_client.post("/v1/messages", headers=native_headers(), json=payload())).status_code == 200
    other_model = {**payload("continue"), "model": "anthropic/claude-sonnet-5"}
    assert (await async_client.post("/v1/messages", headers=native_headers(), json=other_model)).status_code == 404
    async with SessionLocal() as session:
        await session.execute(update(ClaudeResourceOrigin).values(expires_at=utcnow() - timedelta(seconds=1)))
        await session.commit()
    assert (
        await async_client.post("/v1/messages", headers=native_headers(), json=payload("continue"))
    ).status_code == 404
    assert len(captured) == 1


async def test_paused_thread_owner_is_never_replaced(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    assert (await async_client.post("/v1/messages", headers=native_headers(), json=payload())).status_code == 200
    await async_client.patch(f"/api/claude-accounts/{captured[0][0]}", json={"isEnabled": False})
    response = await async_client.post("/v1/messages", headers=native_headers(), json=payload("continue"))
    assert response.status_code == 503
    assert len(captured) == 1


@pytest.mark.parametrize("missing", [True, False])
async def test_upstream_thread_404_is_request_scoped_and_full_history_can_replay(
    async_client, pool, monkeypatch, missing
):
    from app.modules.claude import transport

    captured, _ = install_upstream(monkeypatch)
    assert (await async_client.post("/v1/messages", headers=native_headers(), json=payload())).status_code == 200
    calls = []

    async def reject(source, *_args, **_kwargs):
        calls.append(source.id)
        raise ModelSourceForwardingError(
            status_code=404,
            upstream_status_code=404,
            payload={
                "type": "error",
                "error": {
                    "type": "not_found_error",
                    "message": ("No thread state was found for previous_message_id" if missing else "Model not found"),
                },
            },
        )

    monkeypatch.setattr(transport, "_open_source_stream", reject)
    response = await async_client.post("/v1/messages", headers=native_headers(), json=payload("continue"))
    assert response.status_code == 404, response.text
    assert ("thread_not_found" in response.text) is missing
    assert calls == [captured[0][0]]
    replay, _ = install_upstream(monkeypatch, message_id="msg_replayed")
    response = await async_client.post("/v1/messages", headers=native_headers(), json=payload())
    assert response.status_code == 200, response.text
    assert len(replay) == 1
    async with SessionLocal() as session:
        from app.db.models import ClaudeCooldown

        assert list(await session.scalars(select(ClaudeCooldown))) == []
