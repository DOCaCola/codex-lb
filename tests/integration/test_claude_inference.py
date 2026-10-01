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


@pytest.mark.parametrize(
    "path", ["/v1/messages", "/v1/chat/completions", "/v1/responses", "/backend-api/codex/responses"]
)
@pytest.mark.parametrize("effort", ["none", "medium", "high", None])
async def test_account_reasoning_policy_applies_before_claude_dispatch(async_client, pool, monkeypatch, path, effort):
    from app.modules.claude import transport

    install_upstream(monkeypatch)
    original = transport._open_source_stream
    dispatched = []

    async def send(source, *args, **kwargs):
        dispatched.append(source.id)
        return await original(source, *args, **kwargs)

    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.patch(
        f"/api/claude-accounts/{pool[0]}",
        json={
            "routingPolicy": "burn_first",
            "reasoningRestrictions": {"claude-opus-5": ["medium"]},
        },
    )
    assert response.status_code == 200, response.text
    body = {"model": MODEL, "stream": True}
    if path.endswith("messages"):
        body.update(max_tokens=100, messages=[{"role": "user", "content": "Hi"}])
        if effort == "none":
            body.update(thinking={"type": "disabled"}, output_config={"effort": "high"})
        elif effort:
            body.update(thinking={"type": "adaptive"}, output_config={"effort": effort})
    elif path.endswith("completions"):
        body["messages"] = [{"role": "user", "content": "Hi"}]
        if effort:
            body["reasoning_effort"] = effort
    else:
        body["input"] = "Hi"
        if effort:
            body["reasoning"] = {"effort": effort}
    response = await async_client.post(path, json=body, headers=native_headers() if path.endswith("messages") else {})
    assert response.status_code == 200, response.text
    assert dispatched == [pool[0] if effort == "medium" else pool[1]]


def install_upstream(
    monkeypatch,
    *,
    stop="end_turn",
    truncate=False,
    content=None,
    rejections=0,
    message_id="msg_fixture",
    start_usage=None,
    delta_usage=None,
):
    from app.modules.claude import transport

    captured, closed = [], []

    async def open_stream(source, path, payload, **kwargs):
        captured.append((source.id, path, payload, kwargs["prepared_headers"]))
        if len(captured) <= rejections:
            from app.modules.model_sources.forwarding import ModelSourceForwardingError

            raise ModelSourceForwardingError(
                status_code=400,
                payload={"error": {"message": "Invalid signature in thinking block"}},
                upstream_status_code=400,
            )
        stack = AsyncExitStack()
        stack.callback(lambda: closed.append(source.id))
        events = [
            {"type": "message_start", "message": {"id": message_id, "usage": start_usage or {"input_tokens": 10}}},
            {"type": "ping"},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello from Claude"}},
            {"type": "content_block_stop", "index": 0},
        ]
        if content is not None:
            events = events[:2]
            for index, block in enumerate(content):
                events.extend(
                    [
                        {"type": "content_block_start", "index": index, "content_block": block},
                        {"type": "content_block_stop", "index": index},
                    ]
                )
        if not truncate:
            events.extend(
                [
                    {
                        "type": "message_delta",
                        "delta": {"stop_reason": stop},
                        "usage": delta_usage or {"output_tokens": 7},
                    },
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


@pytest.mark.parametrize("rejections", [1, 2])
async def test_public_native_signature_recovery_is_one_shot(async_client, pool, monkeypatch, rejections):
    captured, closed = install_upstream(monkeypatch, rejections=rejections)
    response = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "max_tokens": 100,
            "stream": True,
            "messages": [
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "old", "signature": "signature"},
                        {"type": "text", "text": "answer"},
                    ],
                },
                {"role": "user", "content": "continue"},
            ],
        },
    )
    assert len(captured) == 2
    assert captured[0][0] == captured[1][0]
    assert captured[0][2]["messages"][1]["content"][0]["type"] == "thinking"
    assert captured[1][2]["messages"][1]["content"] == [{"type": "text", "text": "answer"}]
    assert response.status_code == (200 if rejections == 1 else 400)
    assert len(closed) == (1 if rejections == 1 else 0)


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
    from app.db.models import ClaudeAccount
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        selected = await session.get(ClaudeAccount, captured[0][0])
        assert selected is not None and selected.last_selected_at is not None
    if stream:
        assert '"type":"response.completed"' in response.text or '"type": "response.completed"' in response.text
    else:
        assert response.json()["usage"]["total_tokens"] == 17


@pytest.mark.parametrize(
    "path", ["/v1/responses", "/backend-api/codex/responses", "/v1/chat/completions", "/v1/messages"]
)
async def test_assistant_tail_continuation_is_only_applied_to_translated_routes(async_client, pool, monkeypatch, path):
    captured, closed = install_upstream(monkeypatch)
    history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Progress"}]
    body = {"model": MODEL, "stream": True}
    if path.endswith("messages"):
        body.update(messages=history, max_tokens=100)
    elif path.endswith("completions"):
        body["messages"] = history
    else:
        body["input"] = history
    response = await async_client.post(path, json=body, headers=native_headers() if path.endswith("messages") else {})
    assert response.status_code == 200, response.text
    messages = captured[0][2]["messages"]
    if path.endswith("messages"):
        assert messages == history
    else:
        assert messages[1] == {"role": "assistant", "content": [{"type": "text", "text": "Progress"}]}
        assert len(messages) == 3
        assert messages[2] == {
            "role": "user",
            "content": [{"type": "text", "text": "(continue)", "cache_control": {"type": "ephemeral"}}],
        }
    assert len(closed) == 1


async def test_empty_delta_signed_continuation_does_not_retain_synthetic_user_input(async_client, pool, monkeypatch):
    from tests.integration.model_source_helpers import _enable_api_key_auth

    await _enable_api_key_auth(async_client)
    created = await async_client.post(
        "/api/api-keys/", json={"name": "signed-continuation", "assignedSourceIds": [pool[0]]}
    )
    assert created.status_code == 200, created.text
    headers = {"Authorization": f"Bearer {created.json()['key']}", "session_id": "empty-delta"}
    previous = None
    for turn in range(3):
        captured, closed = install_upstream(
            monkeypatch,
            message_id=f"msg_continuation_{turn}",
            content=[
                {"type": "thinking", "thinking": "preserve", "signature": "signed"},
                {"type": "text", "text": "Progress"},
            ],
        )
        body = {"model": MODEL, "stream": False, "input": "Hello" if turn == 0 else []}
        if previous:
            body["previous_response_id"] = previous
        response = await async_client.post("/v1/responses", headers=headers, json=body)
        assert response.status_code == 200, response.text
        previous = response.json()["id"]
        messages = captured[0][2]["messages"]
        if turn:
            # The normal wire caching policy decorates the final user block.
            messages = [
                {
                    **message,
                    "content": [
                        {key: value for key, value in block.items() if key != "cache_control"}
                        for block in message["content"]
                    ],
                }
                for message in messages
            ]
            assert [message["role"] for message in messages] == ["user", "assistant", "user"]
            assert messages[0]["content"] == [{"type": "text", "text": "Hello"}]
            assert messages[-1]["content"] == [{"type": "text", "text": "(continue)"}]
            assert messages[1]["content"] == [
                block
                for _ in range(turn)
                for block in [
                    {"type": "thinking", "thinking": "preserve", "signature": "signed"},
                    {"type": "text", "text": "Progress"},
                ]
            ]
        assert len(captured) == len(closed) == 1


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("stream", [False, True])
async def test_undeclared_tool_failure_is_structured_and_logged_after_partial_output(
    async_client, pool, monkeypatch, path, stream
):
    captured, closed = install_upstream(
        monkeypatch,
        content=[
            {"type": "text", "text": "Progress"},
            {"type": "tool_use", "id": "call_bad", "name": "unknown_tool", "input": {"secret": "private"}},
        ],
    )
    headers = {"session_id": "projection-failure"}
    response = await async_client.post(path, headers=headers, json={"model": MODEL, "input": "Hello", "stream": stream})
    assert response.status_code == (200 if stream else 502), response.text
    if stream:
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert events[-1] == {
            "type": "error",
            "status": 502,
            "error": {
                "type": "upstream_error",
                "code": "invalid_upstream_response",
                "message": "Claude returned an undeclared tool",
            },
        }
        assert any(event["type"] == "response.output_item.done" for event in events)
        assert not any(event["type"] == "response.completed" for event in events)
    else:
        assert response.json()["error"]["code"] == "invalid_upstream_response"
    assert len(captured) == len(closed) == 1
    logs = (await async_client.get("/api/request-logs")).json()["requests"]
    rows = [row for row in logs if row["model"] == MODEL]
    assert len(rows) == 1 and rows[0]["errorCode"] == "invalid_upstream_response"
    replay = await async_client.post(
        path,
        headers=headers,
        json={
            "model": MODEL,
            "input": [],
            "previous_response_id": "resp_msg_fixture",
            "stream": False,
        },
    )
    assert replay.status_code == 400, replay.text
    assert replay.json()["error"]["code"] == "previous_response_not_found"
    assert len(captured) == 1


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_websocket_projection_failure_then_assistant_tail_recovery_on_same_socket(
    async_client, pool, monkeypatch, path
):
    captured, closed = install_upstream(
        monkeypatch,
        content=[
            {"type": "text", "text": "Progress"},
            {"type": "tool_use", "id": "call_bad", "name": "unknown_tool", "input": {}},
        ],
    )
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"user-agent", b"codex_cli_rs/0.157.0"), (b"session_id", b"interrupted-recovery")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        for turn in range(2):
            if turn:
                recovered, recovered_closed = install_upstream(monkeypatch, message_id="msg_recovered")
            body = {
                "type": "response.create",
                "model": MODEL,
                "input": "Hello"
                if turn == 0
                else [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": [{"type": "output_text", "text": "Progress"}]},
                ],
            }
            await incoming.put({"type": "websocket.receive", "text": json.dumps(body)})
            events = []
            while True:
                frame = await asyncio.wait_for(outgoing.get(), 5)
                assert frame["type"] == "websocket.send", frame
                event = json.loads(frame["text"])
                events.append(event)
                if event["type"] in {"error", "response.completed"}:
                    break
            assert events[-1]["type"] == ("response.completed" if turn else "error")
            if not turn:
                assert events[-1]["error"]["code"] == "invalid_upstream_response"
                assert any(event["type"] == "response.output_item.done" for event in events)
                assert len(closed) == 1
        assert len(captured) == len(recovered) == 1
        messages = recovered[0][2]["messages"]
        assert messages[1]["content"] == [{"type": "text", "text": "Progress"}]
        assert messages[2]["content"] == [
            {"type": "text", "text": "(continue)", "cache_control": {"type": "ephemeral"}}
        ]
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert len(recovered_closed) == 1
    rows = (await async_client.get("/api/request-logs")).json()["requests"]
    rows = [row for row in rows if row["model"] == MODEL]
    assert len(rows) == 2 and {row["status"] for row in rows} == {"error", "ok"}


@pytest.mark.parametrize("surface", ["responses", "messages", "chat"])
@pytest.mark.parametrize(
    "opaque_block",
    [
        {"type": "redacted_thinking", "data": "opaque"},
        {"type": "thinking", "thinking": "", "signature": "signed"},
    ],
)
async def test_claude_public_routes_observe_opaque_output_before_adaptation(
    async_client, pool, monkeypatch, surface, opaque_block
):
    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal
    from app.modules.claude import transport
    from tests.simulation.virtual_time import VirtualClock

    clock = VirtualClock()
    install_upstream(monkeypatch, content=[opaque_block, {"type": "text", "text": "answer"}])
    original_open = transport.open_responses
    original_events = transport._iter_sse_events

    async def open_with_clock(*args, **kwargs):
        return await original_open(*args, **{**kwargs, "clock": clock})

    async def timed_events(*args, **kwargs):
        async for frame in original_events(*args, **kwargs):
            event = json.loads(next(line[6:] for line in frame.splitlines() if line.startswith("data: ")))
            if event["type"] == "content_block_start":
                clock.advance((1 if event["index"] == 0 else 3) - clock.monotonic())
            elif event["type"] == "message_stop":
                clock.advance(4 - clock.monotonic())
            yield frame

    monkeypatch.setattr(transport, "open_responses", open_with_clock)
    monkeypatch.setattr(transport, "_iter_sse_events", timed_events)
    if surface == "messages":
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
        assert opaque_block["type"] in response.text
    elif surface == "chat":
        response = await async_client.post(
            "/v1/chat/completions",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
    else:
        response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert response.status_code == 200, response.text
    assert "answer" in response.text
    async with SessionLocal() as session:
        row = (await session.scalars(select(RequestLog).where(RequestLog.model == MODEL))).one()
        assert (row.latency_first_token_ms, row.latency_ms) == (1000, 4000)
        assert row.output_tokens == 7
        assert row.reasoning_tokens is None


@pytest.mark.parametrize("surface", ["responses", "messages", "chat"])
async def test_claude_public_routes_preserve_cache_write_and_semantic_timing(async_client, pool, monkeypatch, surface):
    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal

    install_upstream(
        monkeypatch,
        start_usage={
            "input_tokens": 100,
            "cache_read_input_tokens": 40,
            "cache_creation_input_tokens": 30,
            "cache_creation": {"ephemeral_5m_input_tokens": 20, "ephemeral_1h_input_tokens": 10},
        },
        delta_usage={"output_tokens": 9},
    )
    if surface == "messages":
        response = await async_client.post(
            "/v1/messages",
            headers=native_headers(),
            json={
                "model": "claude-opus-5",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 100,
                "stream": True,
            },
        )
    elif surface == "chat":
        response = await async_client.post(
            "/v1/chat/completions",
            json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], "stream": False},
        )
    else:
        response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": True})
    assert response.status_code == 200, response.text
    async with SessionLocal() as session:
        row = (
            await session.scalars(select(RequestLog).where(RequestLog.model == MODEL).order_by(RequestLog.id.desc()))
        ).first()
        assert row is not None
        assert (row.input_tokens, row.output_tokens, row.cached_input_tokens) == (170, 9, 40)
        assert (row.cache_creation_tokens, row.cache_creation_5m_tokens, row.cache_creation_1h_tokens) == (30, 20, 10)
        assert row.reasoning_tokens is None
        assert row.latency_ms is not None and row.latency_first_token_ms is not None
        assert row.cost_provenance == "api_equivalent_estimate"
        assert row.cost_usd == pytest.approx((100 * 5 + 40 * 0.5 + 20 * 6.25 + 10 * 10 + 9 * 25) / 1_000_000)


async def test_claude_route_uses_long_context_cache_write_rates(async_client, pool, monkeypatch):
    from app.core.usage import pricing_catalog
    from app.core.usage.pricing import ModelPrice

    monkeypatch.setattr(
        pricing_catalog,
        "_prices",
        {
            "claude-opus-5": ModelPrice(
                1,
                5,
                0.1,
                1.25,
                2,
                long_context_threshold_tokens=100,
                long_context_input_per_1m=2,
                long_context_output_per_1m=10,
                long_context_cached_input_per_1m=0.2,
                long_context_cache_write_5m_per_1m=2.5,
                long_context_cache_write_1h_per_1m=4,
            )
        },
    )
    install_upstream(
        monkeypatch,
        start_usage={
            "input_tokens": 51,
            "cache_read_input_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_creation": {"ephemeral_5m_input_tokens": 20, "ephemeral_1h_input_tokens": 10},
        },
        delta_usage={"output_tokens": 10},
    )
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello"})
    assert response.status_code == 200, response.text
    listed = await async_client.get("/api/request-logs")
    row = next(item for item in listed.json()["requests"] if item["model"] == MODEL)
    assert row["costUsd"] == pytest.approx((102 + 4 + 50 + 40 + 100) / 1_000_000)
    assert row["costBreakdown"]["cacheWriteUsd"] == pytest.approx(90 / 1_000_000)


async def test_unknown_claude_write_ttl_keeps_cost_unknown_and_cost_limit_reserved(async_client, pool, monkeypatch):
    from sqlalchemy import select

    from app.db.models import ApiKeyUsageReservation, RequestLog
    from app.db.session import SessionLocal
    from tests.integration.model_source_helpers import _enable_api_key_auth

    await _enable_api_key_auth(async_client)
    created = await async_client.post(
        "/api/api-keys/",
        json={
            "name": "claude-unpriced-cache-write",
            "assignedSourceIds": [pool[0]],
            "limits": [{"limitType": "cost_usd", "limitWindow": "weekly", "maxValue": 100_000_000}],
        },
    )
    assert created.status_code == 200, created.text
    key = created.json()
    install_upstream(
        monkeypatch,
        start_usage={"input_tokens": 100, "cache_creation_input_tokens": 30},
        delta_usage={"output_tokens": 9},
    )
    response = await async_client.post(
        "/v1/responses",
        headers={"Authorization": f"Bearer {key['key']}"},
        json={"model": MODEL, "input": "Hello", "stream": False},
    )
    assert response.status_code == 200, response.text
    async with SessionLocal() as session:
        row = (await session.scalars(select(RequestLog).where(RequestLog.api_key_id == key["id"]))).one()
        reservation = (
            await session.scalars(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.api_key_id == key["id"]))
        ).one()
        assert row.cache_creation_tokens == 30 and row.cost_usd is None
        assert row.cost_provenance == "unpriced"
        assert reservation.status == "finalized" and reservation.cost_microdollars > 0
    listed = await async_client.get("/api/request-logs", params={"limit": 10})
    assert listed.status_code == 200, listed.text
    entry = next(item for item in listed.json()["requests"] if item["apiKeyId"] == key["id"])
    assert entry["inputTokens"] == 130
    assert entry["cacheCreationTokens"] == 30
    assert entry["costUsd"] is None
    assert entry["costProvenance"] == "unpriced"
    assert entry["costBreakdown"]["totalUsd"] is None


async def test_haiku_budget_reasoning_roundtrips_and_logs_upstream_mode(async_client, pool, monkeypatch):
    from unittest.mock import AsyncMock

    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal
    from app.modules.claude.client import ClaudeClient
    from app.modules.claude.schemas import CatalogModel

    model = "claude-haiku-4-5-20251001"
    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(return_value=[CatalogModel(id=model, display_name="Haiku")]))
    refreshed = await async_client.post(f"/api/claude-accounts/{pool[0]}/refresh")
    assert refreshed.status_code == 200
    selected = await async_client.patch(f"/api/claude-accounts/{pool[0]}", json={"selections": [{"model": model}]})
    assert selected.status_code == 200
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/responses",
        json={
            "model": f"anthropic/{model}",
            "input": "Hello",
            "stream": False,
            "reasoning": {"effort": "medium"},
            "max_output_tokens": 10000,
        },
    )
    assert response.status_code == 200, response.text
    assert captured[0][2]["thinking"] == {"type": "enabled", "budget_tokens": 8192}
    assert captured[0][2]["max_tokens"] == 10000
    async with SessionLocal() as session:
        row = (await session.scalars(select(RequestLog).where(RequestLog.model == f"anthropic/{model}"))).one()
        assert row.reasoning_effort == "medium"
        assert row.upstream_thinking_mode == "enabled"
        assert row.upstream_thinking_budget_tokens == 8192
        assert row.reasoning_tokens is None

    rejected = await async_client.post(
        "/v1/responses",
        json={
            "model": f"anthropic/{model}",
            "input": "Hello",
            "reasoning": {"effort": "medium"},
            "max_output_tokens": 8192,
        },
    )
    assert rejected.status_code == 400
    assert len(captured) == 1


async def test_haiku_continues_unsigned_tool_turn_with_thinking_disabled(async_client, pool, monkeypatch):
    from unittest.mock import AsyncMock

    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal
    from app.modules.claude.client import ClaudeClient
    from app.modules.claude.schemas import CatalogModel

    model = "claude-haiku-4-5-20251001"
    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(return_value=[CatalogModel(id=model, display_name="Haiku")]))
    assert (await async_client.post(f"/api/claude-accounts/{pool[0]}/refresh")).status_code == 200
    selected = await async_client.patch(f"/api/claude-accounts/{pool[0]}", json={"selections": [{"model": model}]})
    assert selected.status_code == 200
    captured, _ = install_upstream(monkeypatch)
    # A Sol tool loop (plaintext reasoning only) continued on Haiku.
    loop = [
        {"role": "user", "content": "inspect the file"},
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "Read it first"}]},
        {"type": "function_call", "name": "read", "call_id": "call_sol", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_sol", "output": "contents"},
    ]
    body = {
        "model": f"anthropic/{model}",
        "stream": False,
        "reasoning": {"effort": "medium"},
        "max_output_tokens": 10000,
        "tools": [{"type": "function", "name": "read", "parameters": {"type": "object"}}],
    }
    response = await async_client.post("/v1/responses", json={**body, "input": loop})
    assert response.status_code == 200, response.text
    assert captured[0][2]["thinking"] == {"type": "disabled"}
    assert "interleaved-thinking-2025-05-14" not in captured[0][3].get("anthropic-beta", "")
    next_turn = [*loop, {"role": "assistant", "content": "Done"}, {"role": "user", "content": "now summarize"}]
    response = await async_client.post("/v1/responses", json={**body, "input": next_turn})
    assert response.status_code == 200, response.text
    assert captured[1][2]["thinking"] == {"type": "enabled", "budget_tokens": 8192}
    async with SessionLocal() as session:
        rows = (await session.scalars(select(RequestLog).order_by(RequestLog.id))).all()
        assert [(row.reasoning_effort, row.upstream_thinking_mode) for row in rows] == [
            ("medium", "disabled"),
            ("medium", "enabled"),
        ]


@pytest.mark.parametrize("sampling", [{"temperature": 0.2}, {"top_p": 0.9}])
async def test_claude_responses_rejects_thinking_sampling_conflicts(async_client, pool, monkeypatch, sampling):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/responses",
        json={"model": MODEL, "input": "Hello", "reasoning": {"effort": "medium"}, **sampling},
    )
    assert response.status_code == 400
    assert response.json()["error"]["param"] == next(iter(sampling))
    assert captured == []


async def test_claude_request_without_thinking_records_unset_upstream_reasoning(async_client, pool, monkeypatch):
    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal

    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": False})
    assert response.status_code == 200, response.text
    assert "thinking" not in captured[0][2]
    async with SessionLocal() as session:
        row = (await session.scalars(select(RequestLog).where(RequestLog.model == MODEL))).one()
        # Left to the model-dependent API default: recorded as unset, not guessed.
        assert row.upstream_thinking_mode is None
        assert row.upstream_reasoning_effort is None


@pytest.mark.parametrize("truncate", [False, True])
async def test_claude_metadata_only_stream_has_duration_without_fabricated_ttft(
    async_client, pool, monkeypatch, truncate
):
    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal

    install_upstream(monkeypatch, content=[{"type": "text", "text": ""}], truncate=truncate)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": True})
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    if truncate:
        assert events[-1]["type"] == "error"
        assert events[-1]["error"]["code"] == "model_source_stream_truncated"
        assert not any(event["type"] == "response.completed" for event in events)
    else:
        assert events[-1]["type"] == "response.completed"
    async with SessionLocal() as session:
        row = (await session.scalars(select(RequestLog).where(RequestLog.model == MODEL))).one()
        assert row.latency_ms is not None
        assert row.latency_first_token_ms is None
        assert row.status == ("error" if truncate else "success")


async def test_pause_turn_not_reported_as_completed(async_client, pool, monkeypatch):
    install_upstream(monkeypatch, stop="pause_turn")
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hello", "stream": False})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "incomplete"
    assert response.json()["incomplete_details"]["reason"] == "pause_turn"


@pytest.mark.parametrize("requested,expected", [(None, 64000), (100000, 100000)])
async def test_translated_output_budget_reaches_upstream(async_client, pool, monkeypatch, requested, expected):
    captured, _ = install_upstream(monkeypatch)
    body = {"model": MODEL, "input": "Hello", "stream": False}
    if requested is not None:
        body["max_output_tokens"] = requested
    response = await async_client.post("/v1/responses", json=body)
    assert response.status_code == 200, response.text
    assert captured[0][2]["max_tokens"] == expected


async def test_native_large_budget_preserved_and_ceiling_enforced(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    body = {
        "model": "claude-opus-5",
        "max_tokens": 100000,
        "stream": True,
        "messages": [{"role": "user", "content": "Hello"}],
    }
    response = await async_client.post("/v1/messages", headers=native_headers(), json=body)
    assert response.status_code == 200, response.text
    assert captured[0][2]["max_tokens"] == 100000
    body["max_tokens"] = 128001
    response = await async_client.post("/v1/messages", headers=native_headers(), json=body)
    assert response.status_code == 400
    assert len(captured) == 1


async def test_malformed_input_never_dispatches(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/responses",
        json={
            "model": MODEL,
            "input": [
                {"type": "function_call_output", "call_id": "", "output": "result"},
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


async def test_native_thinking_can_rebind_when_owner_is_unavailable(async_client, pool, monkeypatch):
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
    assert second.status_code == 200, second.text
    assert len(captured) == 2
    assert captured[1][0] != owner
    assert captured[1][2]["messages"] == messages


async def test_native_child_prefers_parent_account(async_client, pool, monkeypatch):
    from uuid import uuid4

    captured, _ = install_upstream(monkeypatch)
    parent, child = str(uuid4()), str(uuid4())
    body = {
        "model": "claude-opus-5",
        "max_tokens": 100,
        "stream": True,
        "messages": [{"role": "user", "content": "hi"}],
    }
    first = await async_client.post("/v1/messages", headers={"x-claude-code-session-id": parent}, json=body)
    assert first.status_code == 200, first.text
    body["metadata"] = {
        "user_id": json.dumps(
            {
                "device_id": "test-device",
                "session_id": child,
                "parent_session_id": parent,
            }
        )
    }
    second = await async_client.post("/v1/messages", headers={"x-claude-code-session-id": child}, json=body)
    assert second.status_code == 200, second.text
    assert captured[0][0] == captured[1][0]


async def test_native_thinking_after_idle_expiry(async_client, pool, monkeypatch):
    from datetime import timedelta

    from sqlalchemy import update

    from app.core.utils.time import utcnow
    from app.db.models import ClaudeSessionOwner
    from app.db.session import SessionLocal

    captured, _ = install_upstream(monkeypatch)
    body = {
        "model": "claude-opus-5",
        "max_tokens": 100,
        "stream": True,
        "messages": [{"role": "user", "content": "hi"}],
    }
    assert (await async_client.post("/v1/messages", headers=native_headers(), json=body)).status_code == 200
    async with SessionLocal() as session:
        await session.execute(update(ClaudeSessionOwner).values(expires_at=utcnow() - timedelta(seconds=1)))
        await session.commit()
    body["messages"].extend(
        [
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "unchanged", "signature": "original"},
                    {"type": "text", "text": "answer"},
                ],
            },
            {"role": "user", "content": "continue"},
        ]
    )
    response = await async_client.post("/v1/messages", headers=native_headers(), json=body)
    assert response.status_code == 200, response.text
    assert captured[1][2]["messages"] == body["messages"]


@pytest.mark.parametrize("rejections", [1, 2])
async def test_native_json_signature_recovery(async_client, pool, monkeypatch, rejections):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    from app.modules.claude import transport

    requests, closed = [], []

    @asynccontextmanager
    async def post(url, **kwargs):
        requests.append(kwargs["json"])
        rejected = len(requests) <= rejections
        data = (
            {"error": {"message": "Invalid signature in thinking block"}}
            if rejected
            else {
                "id": "msg_done",
                "content": [{"type": "text", "text": "done"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 1},
            }
        )
        try:
            yield SimpleNamespace(status=400 if rejected else 200, headers={}, json=AsyncMock(return_value=data))
        finally:
            closed.append(True)

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(post=post)

    monkeypatch.setattr(transport, "lease_model_source_session", lease)
    response = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "max_tokens": 100,
            "stream": False,
            "messages": [
                {"role": "user", "content": "hi"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "old", "signature": "sig"},
                        {"type": "text", "text": "answer"},
                    ],
                },
                {"role": "user", "content": "continue"},
            ],
        },
    )
    assert len(requests) == len(closed) == 2
    assert response.status_code == (200 if rejections == 1 else 400)
    assert requests[0]["messages"][1]["content"][0]["type"] == "thinking"
    assert requests[1]["messages"][1]["content"] == [{"type": "text", "text": "answer"}]


async def test_native_count_tokens_forwards_json_and_headers_without_generation_usage(async_client, pool, monkeypatch):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    from app.modules.claude import transport

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
            "system": "Count these original instructions",
            "messages": [{"role": "user", "content": "Count"}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"input_tokens": 42}
    assert captured[0][0].endswith("/v1/messages/count_tokens?beta=true")
    assert captured[0][1]["allow_redirects"] is False
    assert response.headers["request-id"] == "native-count"
    assert captured[0][1]["json"]["system"] == "Count these original instructions"
    assert "x-stainless-timeout" not in captured[0][1]["headers"]
    logs = (await async_client.get("/api/request-logs")).json()["requests"]
    assert next(row for row in logs if row["model"] == MODEL)["planType"] == "unknown"


async def test_native_wire_identity_and_features_survive_route(async_client, pool, monkeypatch):
    from copy import deepcopy

    from app.modules.claude.profile import CLI_IDENTITY

    captured, _ = install_upstream(monkeypatch)
    session_id = "bf31a05a-97cd-4b4d-aebd-b70898a26ead"
    headers = native_headers() | {
        "x-claude-code-session-id": session_id,
        "x-client-request-id": "native-request",
        "x-stainless-retry-count": "3",
        "x-claude-code-agent-id": "agent",
        "x-claude-code-compaction": "true",
        "anthropic-beta": " oauth-2025-04-20, future-feature-2026-09-26 ",
    }
    body = {
        "model": "claude-opus-5",
        "system": CLI_IDENTITY,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 100,
        "stream": True,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high"},
        "metadata": {"user_id": json.dumps({"device_id": "device", "session_id": session_id})},
    }
    original = deepcopy(body)
    for _ in range(2):
        response = await async_client.post("/v1/messages", headers=headers, json=body)
        assert response.status_code == 200, response.text
    assert body == original
    first, second = captured
    assert first[0] == second[0]
    wire_body, wire_headers = first[2], first[3]
    wire_session = json.loads(wire_body["metadata"]["user_id"])["session_id"]
    assert wire_session == wire_headers["x-claude-code-session-id"] != session_id
    assert wire_session == second[3]["x-claude-code-session-id"]
    assert wire_headers["x-client-request-id"] == "native-request"
    assert wire_headers["x-stainless-retry-count"] == "3"
    assert wire_headers["x-claude-code-agent-id"] == "agent"
    assert wire_headers["x-claude-code-compaction"] == "true"
    assert set(wire_headers["anthropic-beta"].split(",")) == {"oauth-2025-04-20", "future-feature-2026-09-26"}
    assert wire_body["thinking"] == body["thinking"]
    assert wire_body["output_config"] == body["output_config"]
    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        rows = (await session.scalars(select(RequestLog).where(RequestLog.model == MODEL))).all()
        assert len(rows) == 2
        assert all(row.reasoning_effort == "high" for row in rows)
        assert all(row.upstream_reasoning_effort == "high" for row in rows)
        assert all(row.upstream_thinking_mode == "adaptive" for row in rows)


async def test_native_budget_has_no_invented_effort(async_client, pool, monkeypatch):
    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal

    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10000,
            "thinking": {"type": "enabled", "budget_tokens": 4096},
            "stream": True,
        },
    )
    assert response.status_code == 200, response.text
    assert captured[0][2]["thinking"] == {"type": "enabled", "budget_tokens": 4096}
    async with SessionLocal() as session:
        row = (await session.scalars(select(RequestLog).where(RequestLog.model == MODEL))).one()
        assert row.reasoning_effort is None
        assert row.upstream_reasoning_effort is None
        assert row.upstream_thinking_mode == "enabled"
        assert row.upstream_thinking_budget_tokens == 4096


@pytest.mark.parametrize(
    "user_id",
    [
        "opaque",
        '{"device_id":"d","session_id":"invalid"}',
        '{"device_id":"d","session_id":"bf31a05a-97cd-4b4d-aebd-b70898a26ead"}',
    ],
)
async def test_invalid_native_identity_fails_before_refresh(async_client, pool, monkeypatch, user_id):
    from unittest.mock import AsyncMock

    from app.modules.claude.auth import ClaudeAuth

    refresh = AsyncMock()
    monkeypatch.setattr(ClaudeAuth, "snapshot", refresh)
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "max_tokens": 100,
            "stream": True,
            "messages": [{"role": "user", "content": "Hi"}],
            "metadata": {"user_id": user_id},
        },
    )
    assert response.status_code == 400, response.text
    refresh.assert_not_awaited()
    assert not captured


@pytest.mark.parametrize("title", [False, True])
async def test_native_helper_route_does_not_relocate_or_enable_features(async_client, pool, monkeypatch, title):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    from app.modules.claude import transport
    from app.modules.claude.client import ClaudeClient
    from app.modules.claude.schemas import CatalogModel

    model = "claude-haiku-4-5-20251001"
    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(return_value=[CatalogModel(id=model, display_name="Haiku")]))
    refreshed = await async_client.post(f"/api/claude-accounts/{pool[0]}/refresh")
    assert refreshed.status_code == 200
    selected = await async_client.patch(
        f"/api/claude-accounts/{pool[0]}",
        json={
            "selections": [{"model": model}],
        },
    )
    assert selected.status_code == 200
    captured, _ = install_upstream(monkeypatch)

    @asynccontextmanager
    async def post(url, **kwargs):
        captured.append((pool[0], url, kwargs["json"], kwargs["headers"]))
        yield SimpleNamespace(
            status=200,
            headers={},
            json=AsyncMock(
                return_value={
                    "id": "msg_probe",
                    "content": [{"type": "text", "text": "OK"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                }
            ),
        )

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(post=post)

    monkeypatch.setattr(transport, "lease_model_source_session", lease)
    session_id = "bf31a05a-97cd-4b4d-aebd-b70898a26ead"
    body = {
        "model": model,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "probe"}],
        "metadata": {"user_id": json.dumps({"device_id": "device", "session_id": session_id})},
    }
    if title:
        body.update(
            {
                "system": [{"type": "text", "text": "Generate a short session title."}],
                "messages": [{"role": "user", "content": [{"type": "text", "text": "Name this task"}]}],
                "max_tokens": 32000,
                "stream": True,
                "temperature": 1,
                "tools": [],
                "thinking": {"type": "disabled"},
                "output_config": {
                    "format": {
                        "type": "json_schema",
                        "schema": {
                            "type": "object",
                            "properties": {"title": {"type": "string"}},
                            "required": ["title"],
                            "additionalProperties": False,
                        },
                    }
                },
            }
        )
    response = await async_client.post(
        "/v1/messages",
        json=body,
        headers=native_headers()
        | {
            "x-claude-code-session-id": session_id,
            "x-client-request-id": "helper-request",
            "anthropic-beta": "oauth-2025-04-20,structured-outputs-2025-12-15",
        },
    )
    assert response.status_code == 200, response.text
    wire_body, wire_headers = captured[0][2], captured[0][3]
    assert wire_body.get("system") == body.get("system")
    assert wire_body["messages"] == body["messages"]
    assert wire_body.get("thinking") == body.get("thinking")
    assert wire_body.get("output_config") == body.get("output_config")
    assert wire_headers["anthropic-beta"] == "oauth-2025-04-20,structured-outputs-2025-12-15"
    assert wire_headers["x-client-request-id"] == "helper-request"


async def test_translated_disabled_thinking_does_not_enable_thinking_beta(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/messages",
        json={
            "model": "claude-opus-5",
            "max_tokens": 100,
            "stream": True,
            "messages": [{"role": "user", "content": "Hi"}],
            "thinking": {"type": "disabled"},
            "output_config": {"format": {"type": "json_schema", "schema": {"type": "object"}}},
        },
    )
    assert response.status_code == 200, response.text
    headers = captured[0][3]
    betas = headers["anthropic-beta"].split(",")
    assert "interleaved-thinking-2025-05-14" not in betas
    assert "effort-2025-11-24" not in betas
    assert "structured-outputs-2025-12-15" in betas
    assert "x-stainless-helper-method" not in headers


@pytest.mark.parametrize("switch", ["account", "model", "none"])
@pytest.mark.parametrize(
    "user_input",
    [
        "Continue",
        [
            {
                "type": "function_call_output",
                "id": "fc_task",
                "name": "create_thread",
                "namespace": "codex",
                "call_id": None,
                "output": "Continue",
            }
        ],
    ],
)
async def test_completed_thinking_recovery_through_responses(async_client, pool, monkeypatch, switch, user_input):
    captured, _ = install_upstream(
        monkeypatch,
        content=[
            {"type": "thinking", "thinking": "reason", "signature": "signed"},
            {"type": "text", "text": "visible answer"},
        ],
    )
    headers = {"session_id": "translated-recovery"}
    first = await async_client.post(
        "/v1/responses", headers=headers, json={"model": MODEL, "input": "Hello", "stream": False}
    )
    assert first.status_code == 200, first.text
    original_source = captured[0][0]
    if switch == "account":
        from app.db.models import ModelSource
        from app.db.session import SessionLocal

        async with SessionLocal() as session:
            source = await session.get(ModelSource, original_source)
            source.is_enabled = False
            await session.commit()
    second = await async_client.post(
        "/v1/responses",
        headers=headers,
        json={
            "model": "anthropic/claude-sonnet-5" if switch == "model" else MODEL,
            "input": user_input,
            "stream": False,
            "previous_response_id": first.json()["id"],
        },
    )
    assert second.status_code == 200, second.text
    body = captured[1][2]
    blocks = [block for message in body["messages"] for block in message["content"]]
    assert any(block.get("text") == "visible answer" for block in blocks)
    assert any(block.get("type") == "thinking" for block in blocks) == (switch == "none")
    if switch == "account":
        assert captured[1][0] != original_source


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


async def test_active_thinking_model_switch_rejected_before_dispatch(async_client, pool, monkeypatch):
    from app.core.openai.exceptions import ClientPayloadError
    from app.modules.claude import inference

    rejected = []
    authenticate = inference.authenticate_replay

    def observe(*args, **kwargs):
        try:
            return authenticate(*args, **kwargs)
        except ClientPayloadError as exc:
            rejected.append(str(exc))
            raise

    monkeypatch.setattr(inference, "authenticate_replay", observe)
    captured, _ = install_upstream(
        monkeypatch,
        content=[
            {"type": "thinking", "thinking": "reason", "signature": "signed"},
            {"type": "text", "text": "answer"},
        ],
    )
    headers = {"session_id": "active-recovery"}
    first = await async_client.post(
        "/v1/responses", headers=headers, json={"model": MODEL, "input": "Hello", "stream": False}
    )
    assert first.status_code == 200, first.text
    second = await async_client.post(
        "/v1/responses",
        headers=headers,
        json={"model": "anthropic/claude-sonnet-5", "input": first.json()["output"], "stream": False},
    )
    assert second.status_code == 400, second.text
    assert rejected == ["Active Claude reasoning or search requires its original model"]
    assert len(captured) == 1


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("search", [None, False, True])
@pytest.mark.parametrize("failover", [False, 429, 401, 529, "capacity", "overage", "mixed"])
async def test_websocket_claude_roundtrip_and_continuation(async_client, pool, monkeypatch, path, search, failover):
    from tests.unit.test_claude_search import search_content

    captured, closed = install_upstream(monkeypatch, content=search_content() if search else None)
    from app.db.models import ClaudeAccount
    from app.db.session import SessionLocal
    from app.modules.claude import transport
    from app.modules.claude.schemas import AccountState
    from tests.integration.test_claude_request_plans import set_plan

    await set_plan([pool[0]], "pro")
    await set_plan([pool[1]], "max_20x")

    send_with_headers = transport._open_source_stream

    async def observed_send(*args, **kwargs):
        stack, response, extra = await send_with_headers(*args, **kwargs)
        response.headers["anthropic-ratelimit-unified-5h-utilization"] = "0.25"
        return stack, response, extra

    monkeypatch.setattr(transport, "_open_source_stream", observed_send)
    if failover == "capacity":
        from app.modules.proxy import api, source_admission
        from tests.integration.test_claude_capacity import configure

        await configure(async_client, pool)
        bulkhead = source_admission.SourceBulkhead()
        monkeypatch.setattr(source_admission, "_BULKHEAD", bulkhead)
        claim = api.try_claim_source_admission
        full = []

        def claim_available(source):
            if not full:
                full.append(source.id)
                bulkhead.try_acquire(source.id, 1)
            return claim(source)

        monkeypatch.setattr(api, "try_claim_source_admission", claim_available)
    elif failover:
        from unittest.mock import AsyncMock

        from app.modules.claude import transport
        from app.modules.claude.client import ClaudeClient
        from app.modules.model_sources.forwarding import ModelSourceForwardingError
        from tests.claude_quota_helpers import overage_headers
        from tests.integration.test_claude_auth_recovery import rotated

        original = transport._open_source_stream
        refused = []
        if failover == 401:
            monkeypatch.setattr(ClaudeClient, "refresh", AsyncMock(side_effect=rotated))

        async def send(source, *args, **kwargs):
            if not refused:
                refused.append(source.id)
                raise ModelSourceForwardingError(
                    status_code=429 if failover in {"overage", "mixed"} else failover,
                    upstream_status_code=429 if failover in {"overage", "mixed"} else failover,
                    payload={"error": {"message": "refused"}},
                    upstream_headers=overage_headers(mixed=failover == "mixed")
                    if failover in {"overage", "mixed"}
                    else {},
                )
            assert (source.id == refused[0]) == (failover in {401, 529})
            return await original(source, *args, **kwargs)

        monkeypatch.setattr(transport, "_open_source_stream", send)
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
            if search is not None:
                payload["tools"] = [{"type": "web_search", "external_web_access": search}]
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
        if search:
            assert captured[1][2]["messages"][1]["content"][:2] == search_content()[:2]
        elif search is False:
            assert "tools" not in captured[0][2]
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert len(closed) == 2

    logs = (await async_client.get("/api/request-logs")).json()["requests"]
    plans = dict(zip(pool, ("pro", "max_20x"), strict=True))
    claude_logs = [row for row in logs if row["model"] == MODEL]
    assert claude_logs
    assert all(row["planType"] == plans[row["modelSourceId"]] for row in claude_logs)

    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, captured[-1][0])
        state = AccountState.model_validate_json(row.state_json)
    assert state.header_usage["five_hour"].window.utilization == 25
    if failover in {"overage", "mixed"}:
        from datetime import UTC, datetime, timedelta

        from tests.integration.test_claude_routing import choose

        later = datetime.now(UTC) + timedelta(hours=3)
        if failover == "overage":
            assert await choose(model="anthropic/claude-sonnet-5", preferred_source_id=refused[0]) == refused[0]
        assert await choose(model="anthropic/claude-sonnet-5", preferred_source_id=refused[0], now=later) == refused[0]
        assert await choose(preferred_source_id=refused[0], now=later) != refused[0]


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
                b'event: content_block_start\ndata: {"type":"content_block_start",'
                b'"index":0,"content_block":{"type":"text","text":""}}\n\n'
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
    assert [level["effort"] for level in claude["supported_reasoning_levels"]] == [
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ]
    assert claude["default_reasoning_level"] == "high"
