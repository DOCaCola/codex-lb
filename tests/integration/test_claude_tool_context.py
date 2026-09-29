"""Standalone Codex context and real Claude tool cycles on public Responses routes."""

import asyncio
import json

import pytest

from tests.integration import test_claude_routing as routing_fixtures
from tests.integration.test_claude_inference import install_upstream

MODEL = routing_fixtures.MODEL
pool = routing_fixtures.pool

pytestmark = pytest.mark.integration

SEED = {"type": "function_call_output", "call_id": "delegation-seed", "output": "Delegated task context"}
TASK = {
    "type": "function_call_output",
    "id": "fc_task",
    "name": "create_thread",
    "namespace": "codex",
    "output": "New task",
}
TASKS = [TASK, {**TASK, "call_id": None}, {**TASK, "call_id": ""}, {**TASK, "call_id": " \t"}]
CALL = {"type": "function_call", "call_id": "active-call", "name": "run", "arguments": "{}"}
RESULT = {"type": "function_call_output", "call_id": "active-call", "output": "Actual tool result"}
PATHS = ["/v1/responses", "/backend-api/codex/responses"]


def assert_seed(body, *, last=False, seed=SEED):
    blocks = body["messages"][0]["content"]
    if seed != SEED:
        assert blocks[0] == {
            "type": "text",
            "text": seed["output"],
            **({"cache_control": {"type": "ephemeral"}} if last else {}),
        }
        assert all(block["type"] != "tool_result" for block in blocks)
        return
    assert blocks[0] == {"type": "text", "text": "[Standalone function_call_output: call_id=delegation-seed]"}
    assert blocks[1] == {
        "type": "text",
        "text": SEED["output"],
        **({"cache_control": {"type": "ephemeral"}} if last else {}),
    }
    assert all(block["type"] != "tool_result" for block in blocks)


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("seed", [SEED, *TASKS])
async def test_http_delegation_seed_is_context(async_client, pool, monkeypatch, path, stream, seed):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(
        path,
        json={
            "model": MODEL,
            "input": [seed, {"role": "user", "content": "Continue"}],
            "stream": stream,
        },
    )
    assert response.status_code == 200, response.text
    assert "Hello from Claude" in response.text
    assert len(captured) == 1 and len(closed) == 1
    assert_seed(captured[0][2], seed=seed)
    assert captured[0][2]["messages"][0]["content"][-1] == {
        "type": "text",
        "text": "Continue",
        "cache_control": {"type": "ephemeral"},
    }


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize(
    "items,reason",
    [
        ([CALL, RESULT, RESULT], "duplicate_result"),
        ([RESULT, CALL], "out_of_order_result"),
        ([CALL, SEED], "interrupted_tool_cycle"),
        ([{**RESULT, "call_id": ""}], "invalid_call_id"),
        ([{**TASK, "call_id": 1}], "invalid_call_id"),
        ([{**TASK, "namespace": None}], "invalid_call_id"),
        ([{**TASK, "output": " "}], "invalid_call_id"),
        ([{**TASK, "output": [{"type": "text", "text": "keep"}, {"type": "unknown"}]}], "invalid_call_id"),
        ([CALL, TASK], "interrupted_tool_cycle"),
    ],
)
async def test_http_invalid_tool_cycles_never_dispatch(async_client, pool, monkeypatch, caplog, path, items, reason):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(path, json={"model": MODEL, "input": items})
    assert response.status_code == 400, response.text
    assert reason in response.json()["error"]["message"]
    assert not captured and not closed
    diagnostic = next(
        record.getMessage() for record in caplog.records if "claude_tool_output_rejected" in record.message
    )
    assert "request_id=None" not in diagnostic


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("kind", ["function_call_output", "custom_tool_call_output"])
async def test_http_standalone_image_and_text_are_preserved(async_client, pool, monkeypatch, path, kind):
    captured, _ = install_upstream(monkeypatch)
    data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lwAAAABJRU5ErkJggg=="
    response = await async_client.post(
        path,
        json={
            "model": MODEL,
            "input": [
                {
                    "type": kind,
                    "call_id": "seed-image",
                    "output": [
                        {"type": "input_text", "text": "Image task context"},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{data}"},
                    ],
                }
            ],
            "stream": True,
        },
    )
    assert response.status_code == 200, response.text
    blocks = captured[0][2]["messages"][0]["content"]
    assert blocks == [
        {"type": "text", "text": f"[Standalone {kind}: call_id=seed-image]"},
        {"type": "text", "text": "Image task context"},
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": data},
            "cache_control": {"type": "ephemeral"},
        },
    ]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("stream", [False, True])
async def test_http_external_task_preserves_text_images_in_established_history(
    async_client, pool, monkeypatch, path, stream
):
    from app.core.config.settings import get_settings
    from app.modules.proxy._service.websocket.replay_store import HTTPFallbackReplayStore, ReplayScope

    captured, closed = install_upstream(monkeypatch)
    headers = {"session_id": "established-task"}
    first = await async_client.post(path, headers=headers, json={"model": MODEL, "input": "Before", "stream": True})
    assert first.status_code == 200, first.text
    events = [
        json.loads(line[6:]) for line in first.text.splitlines() if line.startswith("data: ") and line != "data: [DONE]"
    ]
    response_id = next(event["response"]["id"] for event in events if event["type"] == "response.completed")
    task = {
        **TASK,
        "call_id": None,
        "output": [
            {"type": "output_text", "text": "Before image"},
            {"type": "input_image", "image_url": "https://example.com/task.png", "detail": "high"},
            {"type": "input_text", "text": "After image"},
        ],
    }
    second = await async_client.post(
        path,
        headers=headers,
        json={"model": MODEL, "previous_response_id": response_id, "input": [task], "stream": stream},
    )
    assert second.status_code == 200, second.text
    assert len(captured) == len(closed) == 2
    messages = captured[-1][2]["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant", "user"]
    assert messages[-1]["content"] == [
        {"type": "text", "text": "Before image"},
        {"type": "image", "source": {"type": "url", "url": "https://example.com/task.png"}},
        {"type": "text", "text": "After image", "cache_control": {"type": "ephemeral"}},
    ]
    store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
    retained = await store.load(ReplayScope(None, "established-task"), response_id)
    assert retained is not None
    assert retained.input[-1] == task


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("seed", [SEED, *TASKS])
async def test_http_continuation_restores_real_tool_pair_after_seed(async_client, pool, monkeypatch, path, seed):
    from app.core.config.settings import get_settings
    from app.modules.claude.protocol import ToolIdentity
    from app.modules.proxy._service.websocket.replay_store import HTTPFallbackReplayStore, ReplayScope

    captured, _ = install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {
                "type": "tool_use",
                "id": "active-call",
                "name": ToolIdentity("run", None, False).wire_name,
                "input": {},
            }
        ],
    )
    tools = [{"type": "function", "name": "run", "parameters": {"type": "object", "properties": {}}}]
    headers = {"session_id": "tool-context"}
    first = await async_client.post(
        path, headers=headers, json={"model": MODEL, "input": [seed], "tools": tools, "stream": True}
    )
    assert first.status_code == 200, first.text
    events = [
        json.loads(line[6:]) for line in first.text.splitlines() if line.startswith("data: ") and line != "data: [DONE]"
    ]
    response_id = next(event["response"]["id"] for event in events if event["type"] == "response.completed")
    store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
    retained = await store.load(ReplayScope(None, "tool-context"), response_id)
    assert retained is not None
    assert retained.input == [seed]
    assert isinstance(retained.output[0], dict)
    assert retained.output[0]["call_id"] == "active-call"
    second_captured, _ = install_upstream(monkeypatch)
    second = await async_client.post(
        path,
        headers=headers,
        json={
            "model": MODEL,
            "previous_response_id": response_id,
            "input": [RESULT],
            "tools": tools,
            "stream": True,
        },
    )
    assert second.status_code == 200, second.text
    assert len(captured) == 1 and len(second_captured) == 1
    assert_seed(second_captured[0][2], last=True, seed=seed)
    messages = second_captured[0][2]["messages"]
    assert messages[1]["content"][0]["type"] == "tool_use"
    assert messages[1]["content"][0]["id"] == "active-call"
    assert messages[2]["content"] == [
        {
            "type": "tool_result",
            "tool_use_id": "active-call",
            "content": [{"type": "text", "text": RESULT["output"]}],
            "cache_control": {"type": "ephemeral"},
        }
    ]


@pytest.mark.parametrize("path", PATHS)
async def test_missing_explicit_continuation_is_not_standalone_context(async_client, pool, monkeypatch, path):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(
        path,
        json={
            "model": MODEL,
            "previous_response_id": "resp_unavailable",
            "input": [RESULT],
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "previous_response_not_found"
    assert not captured and not closed


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize(
    "seed,reason",
    [(seed, None) for seed in [SEED, *TASKS]]
    + [(TASK, reason) for reason in ("duplicate_result", "invalid_call_id", "interrupted_tool_cycle")],
)
async def test_websocket_standalone_context_and_strict_pairing(
    async_client, pool, monkeypatch, caplog, path, reason, seed
):
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
        "headers": [(b"user-agent", b"codex_cli_rs/0.159.0"), (b"session_id", b"claude-tool-context-ws")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        previous = None
        rejected_input = {
            "duplicate_result": [CALL, RESULT, RESULT],
            "invalid_call_id": [{**TASK, "call_id": 1}],
            "interrupted_tool_cycle": [CALL, TASK],
        }
        for turn in range(1 if reason else 2):
            payload = {
                "type": "response.create",
                "model": MODEL,
                "input": rejected_input[reason] if reason else [seed] if turn == 0 else [TASK],
            }
            if previous:
                payload["previous_response_id"] = previous
            await incoming.put({"type": "websocket.receive", "text": json.dumps(payload)})
            while True:
                frame = await asyncio.wait_for(outgoing.get(), 5)
                assert frame["type"] == "websocket.send", frame
                event = json.loads(frame["text"])
                if reason:
                    assert event["type"] == "error", event
                    assert reason in event["error"]["message"]
                    break
                assert event["type"] != "error", event
                if event["type"] == "response.completed":
                    previous = event["response"]["id"]
                    break
        if reason:
            assert not captured and not closed
            diagnostic = next(
                record.getMessage() for record in caplog.records if "claude_tool_output_rejected" in record.message
            )
            assert "request_id=None" not in diagnostic
        else:
            assert len(captured) == 2
            assert_seed(captured[0][2], last=True, seed=seed)
            assert_seed(captured[1][2], last=True, seed=seed)
            assert captured[1][2]["messages"][-1]["content"] == [
                {"type": "text", "text": TASK["output"], "cache_control": {"type": "ephemeral"}}
            ]
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    assert len(closed) == (0 if reason else 2)
