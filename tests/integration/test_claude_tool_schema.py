import asyncio
import json
from contextlib import AsyncExitStack
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from app.modules.claude import transport
from tests.integration.test_claude_inference import MODEL
from tests.integration.test_claude_inference import pool as pool
from tests.unit.test_claude_tool_schema import declaration

pytestmark = pytest.mark.integration

ARGUMENTS = {"mode": "update", "prompt": "roundtrip"}


def install_tools(monkeypatch, *, invalid=False):
    captured, closed = [], []

    async def open_stream(source, path, payload, **kwargs):
        captured.append(payload)
        stack = AsyncExitStack()
        stack.callback(lambda: closed.append(source.id))
        tool = payload["tools"][0]
        assert not {"oneOf", "anyOf", "allOf"} & tool["input_schema"].keys()
        wire_input = {"arguments": {"mode": "update"} if invalid else ARGUMENTS}
        if not invalid:
            Draft202012Validator(tool["input_schema"]).validate(wire_input)
        text = json.dumps(wire_input)
        events = [
            {"type": "message_start", "message": {"id": f"tool{len(captured)}", "usage": {"input_tokens": 10}}},
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "tool_use",
                    "id": f"call{len(captured)}",
                    "name": tool["name"],
                    "input": {},
                },
            },
            *[
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": text[i : i + 3],
                    },
                }
                for i in range(0, len(text), 3)
            ],
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 10}},
            {"type": "message_stop"},
        ]

        async def chunks(_size):
            for event in events:
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()

        return stack, SimpleNamespace(status=200, headers={}, content=SimpleNamespace(iter_chunked=chunks)), None

    monkeypatch.setattr(transport, "_open_source_stream", open_stream)
    return captured, closed


def sse_events(text):
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ") and line[6:] != "[DONE]"]


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_http_tool_roundtrip_and_durable_continuation(async_client, pool, monkeypatch, path, stream):
    captured, closed = install_tools(monkeypatch)
    response = await async_client.post(
        path, json={"model": MODEL, "input": "Use update", "tools": declaration(), "stream": stream}
    )
    assert response.status_code == 200, response.text
    if stream:
        events = sse_events(response.text)
        terminal = next(e["response"] for e in events if e["type"] == "response.completed")
        deltas = "".join(e["delta"] for e in events if e["type"] == "response.function_call_arguments.delta")
        assert json.loads(deltas) == ARGUMENTS
    else:
        terminal = response.json()
    call = terminal["output"][0]
    assert call["name"] == "automation_update" and call["namespace"] == "codex_app"
    assert json.loads(call["arguments"]) == ARGUMENTS
    follow = await async_client.post(
        path,
        json={
            "model": MODEL,
            "previous_response_id": terminal["id"],
            "tools": declaration(),
            "stream": False,
            "input": [{"type": "function_call_output", "call_id": call["call_id"], "output": "done"}],
        },
    )
    assert follow.status_code == 200, follow.text
    assert captured[1]["messages"][1]["content"][0]["input"] == {"arguments": ARGUMENTS}
    assert len(closed) == 2


async def test_named_schema_error_before_upstream(async_client, pool, monkeypatch):
    captured, _ = install_tools(monkeypatch)
    response = await async_client.post(
        "/v1/responses",
        json={
            "model": MODEL,
            "input": "Hi",
            "tools": declaration({"anyOf": [{"$ref": "https://example.invalid/schema"}]}),
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["param"] == "tools[0].tools[0].parameters"
    assert "codex_app.automation_update" in response.json()["error"]["message"]
    assert captured == []


async def test_native_messages_does_not_adapt_tools(async_client, pool, monkeypatch):
    from tests.integration.test_claude_inference import install_upstream, native_headers
    from tests.unit.test_claude_tool_schema import MODES

    captured, closed = install_upstream(monkeypatch)
    tools = [{"name": "original", "input_schema": MODES}]
    response = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            "model": "claude-opus-5",
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": tools,
            "max_tokens": 100,
            "stream": True,
        },
    )
    assert response.status_code == 200, response.text
    assert captured[0][2]["tools"] == tools
    assert len(closed) == 1


async def test_invalid_generated_arguments_do_not_complete(async_client, pool, monkeypatch):
    captured, closed = install_tools(monkeypatch, invalid=True)
    response = await async_client.post(
        "/v1/responses",
        json={"model": MODEL, "input": "Hi", "tools": declaration(), "stream": True},
    )
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "error"
    assert events[-1]["status"] == 502
    assert events[-1]["error"]["code"] == "invalid_upstream_response"
    body = response.content
    assert b"response.completed" not in body
    assert b"response.function_call_arguments.delta" not in body
    assert b"response.function_call_arguments.done" not in body
    assert len(captured) == len(closed) == 1


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_websocket_tool_roundtrip(async_client, pool, monkeypatch, path):
    captured, closed = install_tools(monkeypatch)
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"user-agent", b"codex_cli_rs/0.159.0"), (b"session_id", b"schema-roundtrip")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        previous = None
        for _ in range(2):
            payload = {
                "type": "response.create",
                "model": MODEL,
                "tools": declaration(),
                "input": "Hi"
                if previous is None
                else [{"type": "function_call_output", "call_id": "call1", "output": "ok"}],
            }
            if previous:
                payload["previous_response_id"] = previous
            await incoming.put({"type": "websocket.receive", "text": json.dumps(payload)})
            arguments = ""
            while True:
                frame = await asyncio.wait_for(outgoing.get(), 5)
                event = json.loads(frame["text"])
                assert event["type"] != "error", event
                if event["type"] == "response.function_call_arguments.delta":
                    arguments += event["delta"]
                if event["type"] == "response.completed":
                    previous = event["response"]["id"]
                    assert json.loads(arguments) == ARGUMENTS
                    assert event["response"]["output"][0]["namespace"] == "codex_app"
                    break
        assert captured[1]["messages"][1]["content"][0]["input"] == {"arguments": ARGUMENTS}
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert len(closed) == 2
