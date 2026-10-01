import asyncio
import json
import math
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config.settings import get_settings
from app.core.crypto import TokenEncryptor
from app.db.session import SessionLocal
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.resources import ResourceScope, record_origins, resolve_origins
from app.modules.proxy.replay_store import HTTPFallbackReplayStore, ReplayScope
from tests.integration.test_claude_inference import install_upstream, native_headers
from tests.integration.test_claude_pool_exhaustion import exhaust
from tests.integration.test_claude_resources import blocks
from tests.integration.test_claude_routing import MODEL
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration
CONVERSATION = "claude-quota-owner"
HEADERS = {"user-agent": "codex_cli_rs/0.157.0", "session_id": CONVERSATION}


def owned_history(source):
    token = ClaudeOpaqueState(TokenEncryptor()).encode(
        OpaqueScope(source, MODEL, "anonymous"),
        {"type": "thinking", "thinking": "private reasoning", "signature": "private signature"},
    )
    return [
        {"role": "user", "content": "Work"},
        {"type": "reasoning", "encrypted_content": token, "summary": []},
        {"type": "function_call", "id": "fc_owner", "call_id": "call_owner", "name": "work", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_owner", "output": "done"},
    ]


def assert_quota_detail(error, deadline, *, native=False):
    assert error["type"] == ("rate_limit_error" if native else "usage_limit_reached")
    assert error["code"] == "previous_response_owner_unavailable"
    assert "plan_type" not in error
    assert "quota-exhausted" in error["message"]
    assert "five_hour" in error["message"]
    assert "private" not in json.dumps(error)
    if deadline is None:
        assert "resets_at" not in error
        assert "resets_in_seconds" not in error
    else:
        assert error["resets_at"] == math.ceil(deadline.timestamp())
        assert 290 <= error["resets_in_seconds"] <= 300


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("known_deadline", [False, True])
@pytest.mark.parametrize("retained", [False, True])
async def test_http_owned_quota_preserves_history_without_dispatch(
    async_client, pool, monkeypatch, path, known_deadline, retained
):
    captured, _ = install_upstream(monkeypatch)
    deadline = datetime.now(UTC) + timedelta(minutes=5) if known_deadline else None
    await exhaust(pool[0], deadline)
    history = owned_history(pool[0])
    original = deepcopy(history)
    store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
    scope = ReplayScope(None, CONVERSATION)
    if retained:
        await store.remember(
            scope, "resp_owner", json.dumps({"model": MODEL, "input": history[:1]}), history[1:3], pool[0]
        )
        payload = {"model": MODEL, "previous_response_id": "resp_owner", "input": history[3:]}
    else:
        payload = {"model": MODEL, "input": history}
    response = await async_client.post(path, headers=HEADERS, json=payload)
    assert response.status_code == 429, response.text
    error = response.json()["error"]
    assert_quota_detail(error, deadline)
    assert all(source not in response.text for source in pool)
    if deadline is None:
        assert "retry-after" not in response.headers
    else:
        assert abs(int(response.headers["retry-after"]) - error["resets_in_seconds"]) <= 1
    assert captured == []  # The healthy alternate must not receive active signed history.
    assert history == original
    if retained:
        saved = await store.load(scope, "resp_owner")
        assert saved is not None and saved.account_id == pool[0]
        assert saved.input + saved.output == original[:3]


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("known_deadline", [False, True])
async def test_websocket_owned_quota_carries_retry_details(async_client, pool, monkeypatch, path, known_deadline):
    captured, _ = install_upstream(monkeypatch)
    deadline = datetime.now(UTC) + timedelta(minutes=5) if known_deadline else None
    await exhaust(pool[0], deadline)
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(key.encode(), value.encode()) for key, value in HEADERS.items()],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        payload = {"type": "response.create", "model": MODEL, "input": owned_history(pool[0])}
        for _ in range(2):
            await incoming.put({"type": "websocket.receive", "text": json.dumps(payload)})
            frame = await asyncio.wait_for(outgoing.get(), 5)
            assert frame["type"] == "websocket.send", frame
            event = json.loads(frame["text"])
            assert event["type"] == "error" and event["status"] == 429, event
            assert_quota_detail(event["error"], deadline)
            if deadline is None:
                assert "headers" not in event
            else:
                assert set(event["headers"]) == {"retry-after"}
                assert abs(int(event["headers"]["retry-after"]) - event["error"]["resets_in_seconds"]) <= 1
        assert captured == []
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("path", ["/v1/messages", "/v1/messages/count_tokens"])
async def test_native_resource_owner_quota_is_429(async_client, pool, monkeypatch, path):
    captured, _ = install_upstream(monkeypatch)
    resource_scope = ResourceScope("anonymous", MODEL)
    await record_origins(resource_scope, pool[0], {"content": blocks()})
    deadline = datetime.now(UTC) + timedelta(minutes=5)
    await exhaust(pool[0], deadline)
    response = await async_client.post(
        path,
        headers=native_headers(),
        json={
            "model": MODEL,
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Search"},
                {"role": "assistant", "content": blocks()},
                {"role": "user", "content": "Continue"},
            ],
        },
    )
    assert response.status_code == 429, response.text
    assert response.json()["type"] == "error"
    assert_quota_detail(response.json()["error"], deadline, native=True)
    assert 290 <= int(response.headers["retry-after"]) <= 300
    assert captured == []
    async with SessionLocal() as session:
        assert await resolve_origins(session, resource_scope.keys(frozenset({"srv1"}))) == pool[0]


async def test_paused_signed_owner_remains_503(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    await async_client.patch(f"/api/claude-accounts/{pool[0]}", json={"isEnabled": False})
    response = await async_client.post(
        "/backend-api/codex/responses", headers=HEADERS, json={"model": MODEL, "input": owned_history(pool[0])}
    )
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "previous_response_owner_unavailable"
    assert response.json()["error"]["type"] == "server_error"
    assert "resets_at" not in response.json()["error"]
    assert "retry-after" not in response.headers
    assert captured == []
