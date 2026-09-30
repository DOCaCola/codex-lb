"""Project local compaction markers without losing retained conversation state."""

import asyncio
import json
from contextlib import asynccontextmanager
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

from app.core.config.settings import get_settings
from app.core.openai.compaction import decode_codex_lb_compaction_summary, encode_codex_lb_compaction_summary
from app.core.openai.models import OpenAIResponsePayload
from app.core.openai.requests import sanitize_native_responses_input
from app.modules.proxy import service as proxy_service
from app.modules.proxy._service.websocket.replay_store import HTTPFallbackReplayStore, ReplayScope
from tests.integration import test_claude_provider_history as provider_fixtures
from tests.integration.model_source_helpers import _create_model_source, stub_source_upstreams
from tests.integration.test_claude_inference import install_upstream
from tests.integration.test_proxy_affinity_observation import _import_synthetic_account
from tests.integration.test_proxy_affinity_websocket_observation import SyntheticUpstream

MODEL = provider_fixtures.MODEL
opus_pool = provider_fixtures.opus_pool
HEADERS = {"session_id": "local-compaction-markers"}
PATHS = ["/v1/responses", "/backend-api/codex/responses"]
pytestmark = pytest.mark.integration


def history():
    return [
        {"type": "context_compaction", "id": "cmp_private", "encrypted_content": None},
        {"role": "user", "content": "PRIVATE_SUMMARY: retain the original decision"},
        {"type": "function_call", "call_id": "call_private", "name": "lookup", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_private", "output": "PRIVATE_TOOL_RESULT"},
        {"role": "user", "content": "Continue the task"},
    ]


def request_body():
    return {"model": MODEL, "instructions": "Keep all context", "input": history(), "stream": False}


def assert_projected(body):
    wire = json.dumps(body)
    assert "context_compaction" not in wire and "cmp_private" not in wire
    assert "PRIVATE_SUMMARY: retain the original decision" in wire
    blocks = [block for message in body["messages"] for block in message["content"]]
    assert [block["id"] for block in blocks if block["type"] == "tool_use"] == ["call_private"]
    assert [block["tool_use_id"] for block in blocks if block["type"] == "tool_result"] == ["call_private"]
    result = next(block for block in blocks if block["type"] == "tool_result")
    assert result["content"] == [{"type": "text", "text": "PRIVATE_TOOL_RESULT"}]


async def assert_retained(response_id, original):
    store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
    retained = await store.load(ReplayScope(None, HEADERS["session_id"]), response_id)
    assert retained is not None
    assert retained.expand([])[: len(original)] == original


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("stream", [False, True])
async def test_http_marker_projection_and_retained_replay(async_client, opus_pool, monkeypatch, path, stream):
    captured, closed = install_upstream(monkeypatch)
    body = {**request_body(), "stream": stream}
    original = deepcopy(body)
    response = await async_client.post(path, headers=HEADERS, json=body)
    assert response.status_code == 200, response.text
    if stream:
        events = [
            json.loads(line[6:])
            for line in response.text.splitlines()
            if line.startswith("data: ") and line[6:] != "[DONE]"
        ]
        completed = next(event["response"] for event in events if event["type"] == "response.completed")
    else:
        completed = response.json()
    assert_projected(captured[0][2])
    assert body == original
    await assert_retained(completed["id"], original["input"])
    followup = await async_client.post(
        path,
        headers=HEADERS,
        json={"model": MODEL, "previous_response_id": completed["id"], "input": "Another turn", "stream": False},
    )
    assert followup.status_code == 200, followup.text
    assert_projected(captured[1][2])
    await assert_retained(followup.json()["id"], original["input"])
    assert len(captured) == len(closed) == 2


BAD_CHECKPOINTS = [
    {"type": "compaction", "encrypted_content": "PRIVATE_CIPHERTEXT"},
    {"type": "context_compaction", "encrypted_content": "PRIVATE_CIPHERTEXT"},
    {"type": "compaction", "encrypted_content": "clb1:PRIVATE_INVALID!"},
    {"type": "context_compaction", "encrypted_content": ""},
    {"type": "context_compaction", "content": "PRIVATE_CONTEXT"},
    {
        "type": "context_compaction",
        "encrypted_content": encode_codex_lb_compaction_summary("PRIVATE_SUMMARY"),
        "content": "PRIVATE_CONTEXT",
    },
]


def assert_rejected(error, captured, selection, caplog, *, index=5):
    assert error["code"] == "compaction_history_unavailable"
    assert error["param"] == f"input[{index}]"
    assert not captured
    selection.assert_not_awaited()
    assert "compaction_checkpoint_rejected request_id=" in caplog.text
    assert f"input_index={index}" in caplog.text
    assert "PRIVATE" not in caplog.text and "cmp_private" not in caplog.text and "call_private" not in caplog.text


@pytest.mark.parametrize("path", [*PATHS, *(path + "/compact" for path in PATHS)])
@pytest.mark.parametrize("checkpoint", BAD_CHECKPOINTS)
async def test_http_bad_checkpoint_fails_before_authentication(
    async_client, opus_pool, monkeypatch, path, checkpoint, caplog
):
    from app.modules.claude import inference

    captured, _ = install_upstream(monkeypatch)
    selection = AsyncMock(wraps=inference.select_account)
    monkeypatch.setattr(inference, "select_account", selection)
    body = request_body()
    body["input"].append(checkpoint)
    original = deepcopy(body)
    response = await async_client.post(path, headers=HEADERS, json=body)
    assert response.status_code == 400, response.text
    assert_rejected(response.json()["error"], captured, selection, caplog)
    assert body == original


@pytest.mark.parametrize("path", PATHS)
async def test_compact_error_indexes_original_control_and_history_input(
    async_client, opus_pool, monkeypatch, path, caplog
):
    from app.modules.claude import inference

    captured, _ = install_upstream(monkeypatch)
    selection = AsyncMock(wraps=inference.select_account)
    monkeypatch.setattr(inference, "select_account", selection)
    body = request_body()
    body["input"].insert(0, {"type": "additional_tools", "tools": []})
    body["input"].append(BAD_CHECKPOINTS[0])
    response = await async_client.post(path + "/compact", headers=HEADERS, json=body)
    assert response.status_code == 400, response.text
    assert_rejected(response.json()["error"], captured, selection, caplog, index=6)


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("retained", [False, True])
async def test_http_compact_preserves_readable_local_history(async_client, opus_pool, monkeypatch, path, retained):
    captured, closed = install_upstream(monkeypatch)
    body = request_body()
    if retained:
        first = await async_client.post(path, headers=HEADERS, json=body)
        assert first.status_code == 200, first.text
        body = {**body, "input": [], "previous_response_id": first.json()["id"]}
    response = await async_client.post(path + "/compact", headers=HEADERS, json=body)
    assert response.status_code == 200, response.text
    assert_projected(captured[-1][2])
    checkpoint = response.json()["output"][0]
    assert decode_codex_lb_compaction_summary(checkpoint["encrypted_content"]) == "Hello from Claude"
    assert len(captured) == len(closed)


@asynccontextmanager
async def websocket(app, path):
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"user-agent", b"codex_cli_rs/0.159.2"), (b"session_id", HEADERS["session_id"].encode())],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(app(scope, incoming.get, outgoing.put))

    async def turn(body):
        await incoming.put(
            {"type": "websocket.receive", "text": json.dumps({**body, "type": "response.create", "stream": True})}
        )
        while True:
            frame = await asyncio.wait_for(outgoing.get(), 5)
            assert frame["type"] == "websocket.send", frame
            event = json.loads(frame["text"])
            if event["type"] in {"error", "response.failed", "response.completed"}:
                return event

    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        yield turn
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("path", PATHS)
async def test_websocket_marker_replay_and_compact(async_client, opus_pool, monkeypatch, path):
    captured, closed = install_upstream(monkeypatch)
    body = request_body()
    async with websocket(async_client._transport.app, path) as turn:
        first = await turn(body)
        assert first["type"] == "response.completed", first
        assert_projected(captured[-1][2])
        await assert_retained(first["response"]["id"], body["input"])
        second = await turn({"model": MODEL, "previous_response_id": first["response"]["id"], "input": "Continue"})
        assert second["type"] == "response.completed", second
        assert_projected(captured[-1][2])
        await assert_retained(second["response"]["id"], body["input"])
        compact = await turn(
            {
                "model": MODEL,
                "previous_response_id": second["response"]["id"],
                "input": [{"type": "compaction_trigger"}],
            }
        )
        assert compact["type"] == "response.completed", compact
        assert_projected(captured[-1][2])
        assert compact["response"]["output"][0]["type"] == "compaction"
    assert len(captured) == len(closed) == 3


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("checkpoint", BAD_CHECKPOINTS)
async def test_websocket_bad_checkpoint_is_indexed(async_client, opus_pool, monkeypatch, path, checkpoint, caplog):
    from app.modules.claude import inference

    captured, _ = install_upstream(monkeypatch)
    selection = AsyncMock(wraps=inference.select_account)
    monkeypatch.setattr(inference, "select_account", selection)
    body = request_body()
    body["input"].append(checkpoint)
    async with websocket(async_client._transport.app, path) as turn:
        event = await turn(body)
        assert event["type"] == "error", event
        assert_rejected(event["error"], captured, selection, caplog)


@pytest.mark.parametrize("path", [*PATHS, *(path + "/compact" for path in PATHS)])
async def test_native_http_marker_input_is_unchanged(async_client, monkeypatch, path):
    await _import_synthetic_account(async_client)
    captured = []

    async def stream(payload, *args, **kwargs):
        captured.append(sanitize_native_responses_input(payload.to_payload())["input"])
        yield 'data: {"type":"response.completed","response":{"id":"resp_native","status":"completed","output":[]}}\n\n'

    async def compact(payload, *args, **kwargs):
        captured.append(sanitize_native_responses_input(payload.to_payload())["input"])
        return OpenAIResponsePayload.model_validate({"output": []})

    monkeypatch.setattr(proxy_service, "core_stream_responses", stream)
    monkeypatch.setattr(proxy_service, "core_compact_responses", compact)
    original = history()
    response = await async_client.post(
        path, headers=HEADERS, json={**request_body(), "model": "gpt-6.1-sol", "stream": True}
    )
    assert response.status_code == 200, response.text
    expected = sanitize_native_responses_input(
        {"input": original, "store": None if path.endswith("/compact") else False}
    )
    assert captured == [expected["input"]]


@pytest.mark.parametrize("path", PATHS)
async def test_native_websocket_marker_input_is_unchanged(async_client, monkeypatch, path):
    await _import_synthetic_account(async_client)
    captured = []

    class RecordingUpstream(SyntheticUpstream):
        async def send_text(self, text):
            captured.append(json.loads(text)["input"])
            await super().send_text(text)

    async def connect(*args, **kwargs):
        return RecordingUpstream()

    monkeypatch.setattr(proxy_service, "connect_responses_websocket", connect)
    async with websocket(async_client._transport.app, path) as turn:
        completed = await turn({**request_body(), "model": "gpt-6.1-sol"})
        assert completed["type"] == "response.completed", completed
    expected = sanitize_native_responses_input({"input": history(), "store": False})
    assert captured == [expected["input"]]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("transport", ["http", "websocket"])
async def test_compatible_source_responses_project_markers(async_client, path, transport):
    captured = []

    async def handler(request):
        captured.append(await request.json())
        event = {
            "type": "response.completed",
            "response": {
                "id": "resp_source",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 10, "output_tokens": 7, "total_tokens": 17},
            },
        }
        response = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        await response.write(f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n".encode())
        await response.write_eof()
        return response

    async with stub_source_upstreams() as start:
        base_url = await start(handler)
        await _create_model_source(
            async_client,
            name="marker-source",
            model="marker-model",
            base_url=base_url,
            supports_responses=True,
        )
        body = {**request_body(), "model": "marker-model", "stream": True}
        if transport == "http":
            response = await async_client.post(path, headers=HEADERS, json=body)
            assert response.status_code == 200, response.text
            assert "response.completed" in response.text
        else:
            async with websocket(async_client._transport.app, path) as turn:
                event = await turn(body)
                assert event["type"] == "response.completed", event
    assert len(captured) == 1
    wire = json.dumps(captured[0])
    assert "context_compaction" not in wire and "cmp_private" not in wire
    assert "PRIVATE_SUMMARY" in wire and "PRIVATE_TOOL_RESULT" in wire and "call_private" in wire
    assert captured[0]["input"] == history()[1:]
