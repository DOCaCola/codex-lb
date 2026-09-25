import asyncio
import json
from contextlib import AsyncExitStack
from types import SimpleNamespace

import pytest
from pydantic import JsonValue

from tests.integration import test_claude_routing as routing_fixtures

MODEL = routing_fixtures.MODEL
pool = routing_fixtures.pool

pytestmark = pytest.mark.integration


def install_upstream(monkeypatch, *, stop="end_turn", truncate=False):
    from app.modules.claude import transport

    captured, closed = [], []

    async def open_stream(source, path, payload, **kwargs):
        captured.append((source.id, path, payload, kwargs["prepared_headers"]))
        stack = AsyncExitStack()
        stack.callback(lambda: closed.append(source.id))
        events = [
            {"type": "message_start", "message": {"id": "msg_fixture", "usage": {"input_tokens": 10}}},
            {"type": "ping"},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello from Claude"}},
            {"type": "content_block_stop", "index": 0},
        ]
        if not truncate:
            events.extend(
                [
                    {"type": "message_delta", "delta": {"stop_reason": stop}, "usage": {"output_tokens": 7}},
                    {"type": "message_stop"},
                ]
            )

        async def chunks(_size):
            for event in events:
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()

        response = SimpleNamespace(
            status=200,
            headers={"anthropic-ratelimit-requests-remaining": "10"},
            content=SimpleNamespace(iter_chunked=chunks),
        )
        return stack, response, None

    monkeypatch.setattr(transport, "_open_source_stream", open_stream)
    return captured, closed


@pytest.mark.parametrize("stream", [True, False])
async def test_responses_route_reaches_claude_with_owned_cleanup(async_client, pool, monkeypatch, stream):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": stream})
    assert response.status_code == 200, response.text
    assert "Hello from Claude" in response.text
    assert len(captured) == 1
    assert closed == [captured[0][0]]
    assert captured[0][2]["model"] == "claude-opus-5"
    assert captured[0][3]["authorization"] in {"Bearer access-account-a", "Bearer access-account-b"}
    if stream:
        assert '"type":"response.completed"' in response.text or '"type": "response.completed"' in response.text
    else:
        assert response.json()["usage"]["total_tokens"] == 17


async def test_pause_turn_not_reported_as_completed(async_client, pool, monkeypatch):
    install_upstream(monkeypatch, stop="pause_turn")
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": False})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "incomplete"
    assert response.json()["incomplete_details"]["reason"] == "pause_turn"


async def test_malformed_input_never_dispatches(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/responses",
        json={
            "model": MODEL,
            "input": [
                {"type": "function_call_output", "call_id": "missing", "output": "result"},
            ],
            "stream": False,
        },
    )
    assert response.status_code == 400, response.text
    assert not captured and not closed


async def test_nonstream_truncation_is_error_and_closes_transport(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch, truncate=True)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": False})
    assert response.status_code == 502, response.text
    assert closed == [captured[0][0]]


def native_headers():
    return {
        "User-Agent": "claude-cli/2.1.282 (external, cli)",
        "x-app": "cli",
        "x-stainless-lang": "js",
        "anthropic-beta": "oauth-2025-04-20",
        "x-claude-code-session-id": "native-thread",
    }


async def test_native_messages_preserves_body_and_pings(async_client, pool, monkeypatch):
    from app.modules.claude.profile import CLI_IDENTITY

    captured, closed = install_upstream(monkeypatch)
    system = [
        {"type": "text", "text": CLI_IDENTITY},
        {"type": "text", "text": "Original instructions", "cache_control": {"type": "ephemeral"}},
    ]
    response = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "system": system,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 100,
            "stream": True,
        },
    )
    assert response.status_code == 200, response.text
    assert "event: message_stop" in response.text
    assert "event: ping" in response.text
    assert "response.completed" not in response.text
    assert captured[0][2]["system"] == system
    assert response.headers["anthropic-ratelimit-requests-remaining"] == "10"
    assert closed == [captured[0][0]]


async def test_native_stream_truncation_returns_native_error_and_closes_transport(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch, truncate=True)
    response = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 100,
            "stream": True,
        },
    )
    assert response.status_code == 200, response.text
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1] == {
        "type": "error",
        "error": {"type": "api_error", "message": "Claude stream ended before message_stop"},
    }
    assert "response.failed" not in response.text
    assert "message_stop\n" not in response.text
    assert closed == [captured[0][0]]


async def test_native_signed_history_keeps_owner_when_other_account_is_available(async_client, pool, monkeypatch):
    from app.modules.claude.profile import CLI_IDENTITY

    captured, _ = install_upstream(monkeypatch)
    body: dict[str, JsonValue] = {
        "model": "claude-opus-5",
        "system": CLI_IDENTITY,
        "max_tokens": 100,
        "stream": True,
        "messages": [{"role": "user", "content": "Hi"}],
    }
    first = await async_client.post("/v1/messages", headers=native_headers(), json=body)
    assert first.status_code == 200, first.text
    owner = captured[0][0]
    messages = body["messages"]
    assert isinstance(messages, list)
    messages.extend(
        [
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "signed", "signature": "sig"},
                    {"type": "text", "text": "Hello"},
                ],
            },
            {"role": "user", "content": "Continue"},
        ]
    )
    await async_client.patch(f"/api/claude-accounts/{owner}", json={"isEnabled": False})
    second = await async_client.post("/v1/messages", headers=native_headers(), json=body)
    assert second.status_code != 200
    assert len(captured) == 1


async def test_native_count_tokens_forwards_json_and_headers_without_generation_usage(async_client, pool, monkeypatch):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    from app.modules.claude import transport
    from app.modules.claude.profile import CLI_IDENTITY

    captured = []

    @asynccontextmanager
    async def post(url, **kwargs):
        captured.append((url, kwargs))
        yield SimpleNamespace(
            status=200, headers={"request-id": "native-count"}, json=AsyncMock(return_value={"input_tokens": 42})
        )

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(post=post)

    monkeypatch.setattr(transport, "lease_model_source_session", lease)
    response = await async_client.post(
        "/v1/messages/count_tokens",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "system": CLI_IDENTITY,
            "messages": [{"role": "user", "content": "Count"}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"input_tokens": 42}
    assert captured[0][0].endswith("/v1/messages/count_tokens?beta=true")
    assert captured[0][1]["allow_redirects"] is False
    assert response.headers["request-id"] == "native-count"


async def test_claude_continuation_replayed_from_persisted_response(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    first = await async_client.post(
        "/v1/responses",
        headers={"session_id": "continuation"},
        json={"model": MODEL, "input": "Hello", "stream": False},
    )
    second = await async_client.post(
        "/v1/responses",
        headers={"session_id": "continuation"},
        json={
            "model": MODEL,
            "input": "Continue",
            "stream": False,
            "previous_response_id": first.json()["id"],
        },
    )
    assert second.status_code == 200, second.text
    assert len(captured[1][2]["messages"]) == 3
    assert captured[1][2]["messages"][1]["content"][0]["text"] == "Hello from Claude"


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_websocket_claude_roundtrip_and_continuation(async_client, pool, monkeypatch, path):
    captured, closed = install_upstream(monkeypatch)
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"user-agent", b"codex_cli_rs/0.157.0"), (b"session_id", b"claude-ws")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        previous = None
        for turn in range(2):
            payload = {"type": "response.create", "model": MODEL, "input": "Hello" if turn == 0 else "Continue"}
            if previous:
                payload["previous_response_id"] = previous
            await incoming.put({"type": "websocket.receive", "text": json.dumps(payload)})
            while True:
                frame = await asyncio.wait_for(outgoing.get(), 5)
                assert frame["type"] == "websocket.send", frame
                event = json.loads(frame["text"])
                assert event["type"] != "error", event
                if event["type"] == "response.completed":
                    previous = event["response"]["id"]
                    break
        assert len(captured) == 2
        assert len(captured[1][2]["messages"]) == 3
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert len(closed) == 2


@pytest.mark.parametrize("limit", [None, 0, -1, True, 999999])
async def test_native_invalid_output_limit_never_dispatches(async_client, pool, monkeypatch, limit):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/messages", json={"model": MODEL, "max_tokens": limit, "messages": [{"role": "user", "content": "Hi"}]}
    )
    assert response.status_code == 400, response.text
    assert not captured


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
async def test_compaction_uses_claude_summary_and_preserves_context(async_client, pool, monkeypatch, path):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(
        path, json={"model": MODEL, "instructions": "Summarize", "input": "Remember this context"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["object"] == "response.compaction"
    followup = await async_client.post(
        "/v1/responses",
        json={
            "model": MODEL,
            "input": [*response.json()["output"], {"role": "user", "content": "Continue from the summary"}],
            "stream": False,
        },
    )
    assert followup.status_code == 200, followup.text
    assert "Hello from Claude" in json.dumps(captured[1][2]["messages"])
    assert captured[0][2]["model"] == "claude-opus-5"
    assert len(closed) == 2


@pytest.mark.parametrize("path", ["/v1/responses", "/v1/messages"])
async def test_upstream_errors_preserve_status_and_limits(async_client, pool, monkeypatch, path):
    from app.modules.claude import transport
    from app.modules.model_sources.forwarding import ModelSourceForwardingError

    async def fail(*args, **kwargs):
        raise ModelSourceForwardingError(
            status_code=429,
            payload={"error": {"type": "rate_limit_error", "message": "limited"}},
            upstream_status_code=429,
            retry_after="12",
            upstream_headers={"anthropic-ratelimit-requests-remaining": "0"},
        )

    monkeypatch.setattr(transport, "_open_source_stream", fail)
    body = (
        {"model": MODEL, "stream": True, "input": "Hi"}
        if path.endswith("responses")
        else {"model": MODEL, "stream": True, "max_tokens": 100, "messages": [{"role": "user", "content": "Hi"}]}
    )
    response = await async_client.post(path, json=body)
    assert response.status_code == 429, response.text
    assert response.headers["retry-after"] == "12"
    assert response.headers["anthropic-ratelimit-requests-remaining"] == "0"
    if path.endswith("messages"):
        assert response.json()["type"] == "error"


@pytest.mark.parametrize("path", ["/v1/responses", "/v1/messages"])
async def test_real_sse_transport_disconnect_releases_upstream(async_client, pool, path):
    from aiohttp import web

    from app.db.models import ModelSource
    from app.db.session import SessionLocal
    from tests.integration.model_source_helpers import _AsgiStream, stub_source_upstreams

    disconnected = asyncio.Event()
    captured = []

    async def upstream(request):
        captured.append(await request.json())
        assert request.headers["authorization"] in {"Bearer access-account-a", "Bearer access-account-b"}
        assert request.path == "/v1/messages"
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        try:
            await response.write(
                b'event: message_start\ndata: {"type":"message_start",'
                b'"message":{"id":"msg_live","usage":{"input_tokens":4}}}\n\n'
            )
            await asyncio.Event().wait()
        finally:
            disconnected.set()
        return response

    async with stub_source_upstreams() as start:
        url = await start(upstream, handler_cancellation=True, shutdown_timeout=1)
        async with SessionLocal() as session:
            for source_id in pool:
                source = await session.get(ModelSource, source_id)
                assert source is not None
                source.base_url = url.removesuffix("/v1")
            await session.commit()
        body = (
            {"model": MODEL, "stream": True, "input": "Hi"}
            if path.endswith("responses")
            else {"model": MODEL, "stream": True, "max_tokens": 100, "messages": [{"role": "user", "content": "Hi"}]}
        )
        stream = _AsgiStream(async_client._transport.app, path, {}, json.dumps(body).encode())
        task = asyncio.create_task(stream.run())
        try:
            await stream.wait_for_text("response.created" if path.endswith("responses") else "message_start")
            stream.disconnect()
            await asyncio.wait_for(task, 5)
            await asyncio.wait_for(disconnected.wait(), 5)
            assert len(captured) == 1
        finally:
            stream.disconnect()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def test_catalog_orders_native_claude_after_openai_before_other_sources(async_client, pool):
    from tests.integration.model_source_helpers import _create_model_source

    await _create_model_source(
        async_client, name="Other", model="vendor/other", base_url="https://example.invalid/v1", supports_responses=True
    )
    response = await async_client.get("/backend-api/codex/models?client_version=0.157.0")
    assert response.status_code == 200
    entries = response.json()["models"]
    slugs = [entry["slug"] for entry in entries]
    assert slugs.index(MODEL) < slugs.index("vendor/other")
    assert all(index < slugs.index(MODEL) for index, slug in enumerate(slugs) if slug.startswith("gpt-"))
    claude = next(entry for entry in entries if entry["slug"] == MODEL)
    assert claude["prefer_websockets"] is True
    assert [level["effort"] for level in claude["supported_reasoning_levels"]] == ["low", "medium", "high", "max"]
