"""Observed native compaction followed by real source HTTP/WS preparation."""

import asyncio
import json
from contextlib import asynccontextmanager
from copy import deepcopy

import pytest
from aiohttp import web

from app.core.clients.proxy_websocket import UpstreamWebSocketMessage
from app.core.openai.models import CompactResponsePayload
from app.core.openai.requests import ResponsesCompactRequest
from app.modules.proxy import checkpoint_handoff, checkpoint_history
from app.modules.proxy import service as proxy_service
from app.modules.proxy.replay_store import ApiKeyScope, HTTPFallbackReplayStore
from tests.integration import test_claude_provider_history as provider_fixtures
from tests.integration.model_source_helpers import _create_model_source, stub_source_upstreams
from tests.integration.test_claude_inference import install_upstream
from tests.integration.test_proxy_affinity_observation import _import_synthetic_account
from tests.integration.test_proxy_affinity_websocket_observation import SyntheticUpstream

MODEL = provider_fixtures.MODEL
opus_pool = provider_fixtures.opus_pool
PATHS = ["/v1/responses", "/backend-api/codex/responses"]
pytestmark = pytest.mark.integration


def checkpoint():
    return {"id": "cmp_native", "type": "compaction", "encrypted_content": "PRIVATE_NATIVE_CHECKPOINT"}


def history():
    return [
        {"role": "user", "content": "Original decision: keep the evidence"},
        {
            "type": "reasoning",
            "encrypted_content": "PRIVATE_REASONING",
            "summary": [{"type": "summary_text", "text": "Readable reasoning"}],
        },
        {"type": "function_call", "name": "read", "call_id": "call_evidence", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_evidence", "output": "Important tool evidence"},
        {"role": "user", "content": "Latest constraint"},
    ]


@pytest.fixture
async def recovery_env(async_client, opus_pool, monkeypatch, tmp_path):
    monkeypatch.setattr(checkpoint_history, "checkpoint_store", lambda: HTTPFallbackReplayStore(tmp_path))
    monkeypatch.setattr(checkpoint_handoff, "origin_store", lambda: HTTPFallbackReplayStore(tmp_path / "origins"))
    monkeypatch.setattr(checkpoint_handoff, "handoff_store", lambda: HTTPFallbackReplayStore(tmp_path / "handoffs"))
    await _import_synthetic_account(async_client)
    settings = await async_client.put("/api/settings", json={"apiKeyAuthEnabled": True})
    assert settings.status_code == 200, settings.text
    key = await async_client.post("/api/api-keys/", json={"name": "checkpoint-switch"})
    assert key.status_code == 200, key.text
    headers = {"authorization": "Bearer " + key.json()["key"], "session_id": "checkpoint-switch"}
    calls = []

    async def seed_existing_snapshot(payload):
        # These tests exercise already-retained readable snapshots. Production
        # now records only provenance; on-demand generation has separate tests.
        await checkpoint_history.CheckpointHistory(
            HTTPFallbackReplayStore(tmp_path), ApiKeyScope(key.json()["id"])
        ).remember(
            ResponsesCompactRequest.model_validate({**payload, "instructions": payload.get("instructions") or ""}),
            CompactResponsePayload.model_validate({"object": "response.compaction", "output": [checkpoint()]}),
            "existing-snapshot-owner",
        )

    async def native_compact(payload, *args, **kwargs):
        calls.append(deepcopy(payload.model_dump(mode="json")))
        await seed_existing_snapshot(payload.model_dump(mode="json"))
        return CompactResponsePayload.model_validate({"object": "response.compaction", "output": [checkpoint()]})

    monkeypatch.setattr(proxy_service, "core_compact_responses", native_compact)

    async def native_stream(payload, *args, **kwargs):
        # A native HTTP trigger turn streams the checkpoint as an output item;
        # its terminal event may carry an empty output.
        request = payload.to_payload()
        calls.append(deepcopy(request))
        await seed_existing_snapshot(request)
        response = {"id": "resp_compact", "object": "response", "model": request["model"]}
        usage = {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
        for event in (
            {"type": "response.created", "response": {**response, "status": "in_progress"}},
            {"type": "response.output_item.done", "output_index": 0, "item": checkpoint()},
            {
                "type": "response.completed",
                "response": {**response, "status": "completed", "output": [], "usage": usage},
            },
        ):
            yield "data: " + json.dumps(event) + "\n\n"

    monkeypatch.setattr(proxy_service, "core_stream_responses", native_stream)

    class NativeCompactSocket(SyntheticUpstream):
        async def send_text(self, text):
            request = json.loads(text)
            calls.append(request)
            await seed_existing_snapshot(request)
            for kind in ("response.created", "response.completed"):
                self.messages.put_nowait(
                    UpstreamWebSocketMessage(
                        kind="text",
                        text=json.dumps(
                            {
                                "type": kind,
                                "response": {
                                    "id": "resp_compact",
                                    "object": "response",
                                    "model": request["model"],
                                    "status": "completed" if kind.endswith("completed") else "in_progress",
                                    "output": [checkpoint()] if kind.endswith("completed") else [],
                                    "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
                                },
                            }
                        ),
                    )
                )

    async def connect(*args, **kwargs):
        return NativeCompactSocket()

    monkeypatch.setattr(proxy_service, "connect_responses_websocket", connect)
    captured, closed = install_upstream(monkeypatch)
    return headers, calls, captured, closed, tmp_path


@asynccontextmanager
async def websocket(app, path, headers):
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(key.encode(), value.encode()) for key, value in headers.items()],
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
            frame = await asyncio.wait_for(outgoing.get(), 10)
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


def assert_readable(body):
    wire = json.dumps(body)
    for text in (
        "Original decision",
        "Readable reasoning",
        "Important tool evidence",
        "Latest constraint",
        "Keep instructions",
    ):
        assert text in wire
    assert "PRIVATE" not in wire and "encrypted_content" not in wire
    blocks = [part for message in body["messages"] for part in message["content"]]
    assert [part["id"] for part in blocks if part["type"] == "tool_use"] == ["call_evidence"]
    assert [part["tool_use_id"] for part in blocks if part["type"] == "tool_result"] == ["call_evidence"]


@pytest.mark.parametrize("path,trigger", [(path, False) for path in PATHS] + [(PATHS[1], True)])
async def test_native_compact_then_http_source_recovery_and_continuation(async_client, recovery_env, path, trigger):
    headers, calls, captured, closed, directory = recovery_env
    original = history()
    body = {"model": "gpt-5.1", "instructions": "Keep instructions", "input": original}
    if trigger:
        body = {**body, "input": [*original, {"type": "compaction_trigger"}], "stream": True}
    compact = await async_client.post(path if trigger else path + "/compact", headers=headers, json=body)
    assert compact.status_code == 200, compact.text
    assert "PRIVATE_NATIVE_CHECKPOINT" in compact.text
    assert calls[0]["input"][: len(original)] == original
    if trigger:
        # The forwarded turn reaches upstream intact and its streamed
        # checkpoint establishes provenance for the next turn's routing.
        assert calls[0]["input"][-1] == {"type": "compaction_trigger"}
        assert list((directory / "origins").glob("*.replay"))
    assert list(directory.glob("*.replay"))
    switched = await async_client.post(
        path,
        headers=headers,
        json={"model": MODEL, "input": [checkpoint(), {"role": "user", "content": "Continue"}], "stream": False},
    )
    assert switched.status_code == 200, switched.text
    assert_readable(captured[0][2])
    # Recovery must be retained in source continuation, independent of expiry of
    # the native checkpoint record after the successful switch.
    for record in directory.glob("*.replay"):
        record.unlink()
    continued = await async_client.post(
        path,
        headers=headers,
        json={
            "model": MODEL,
            "previous_response_id": switched.json()["id"],
            "input": "Continue again",
            "stream": False,
        },
    )
    assert continued.status_code == 200, continued.text
    assert_readable(captured[1][2])
    assert len(captured) == len(closed) == 2


@pytest.mark.parametrize("path", PATHS)
async def test_native_websocket_compact_then_source_recovery(async_client, recovery_env, path):
    headers, calls, captured, closed, directory = recovery_env
    async with websocket(async_client._transport.app, path, headers) as turn:
        compact = await turn(
            {
                "model": "gpt-5.1",
                "instructions": "Keep instructions",
                "input": [*history(), {"type": "compaction_trigger"}],
            }
        )
        assert compact["type"] == "response.completed", compact
        assert compact["response"]["output"] == [checkpoint()]
        switched = await turn({"model": MODEL, "input": [checkpoint(), {"role": "user", "content": "Continue"}]})
        assert switched["type"] == "response.completed", switched
    assert_readable(captured[0][2])
    assert len(calls) == len(captured) == len(closed) == 1


@pytest.mark.parametrize("path", PATHS)
async def test_native_checkpoint_can_be_compacted_by_source(async_client, recovery_env, path):
    headers, calls, captured, closed, _ = recovery_env
    compact = await async_client.post(
        path + "/compact",
        headers=headers,
        json={"model": "gpt-5.1", "instructions": "Keep instructions", "input": history()},
    )
    assert compact.status_code == 200, compact.text
    switched = await async_client.post(
        path + "/compact",
        headers=headers,
        json={
            "model": MODEL,
            "instructions": "Summarize everything",
            "input": [checkpoint(), {"role": "user", "content": "Continue"}],
        },
    )
    assert switched.status_code == 200, switched.text
    assert switched.json()["output"][0]["encrypted_content"].startswith("clb1:")
    assert_readable(captured[0][2])
    assert len(captured) == len(closed) == 1


async def test_forked_conversation_uses_retained_checkpoint(async_client, recovery_env):
    headers, calls, captured, _, _ = recovery_env
    compact = await async_client.post(
        PATHS[0] + "/compact",
        headers=headers,
        json={"model": "gpt-5.1", "instructions": "Keep instructions", "input": history()},
    )
    assert compact.status_code == 200, compact.text
    response = await async_client.post(
        PATHS[0],
        headers={**headers, "session_id": "forked-thread"},
        json={"model": MODEL, "input": [checkpoint()], "stream": False},
    )
    assert response.status_code == 200, response.text
    assert_readable(captured[0][2])


async def test_other_api_key_cannot_use_retained_checkpoint(async_client, recovery_env):
    headers, calls, captured, _, _ = recovery_env
    compact = await async_client.post(
        PATHS[0] + "/compact",
        headers=headers,
        json={"model": "gpt-5.1", "instructions": "Keep instructions", "input": history()},
    )
    assert compact.status_code == 200, compact.text
    other = await async_client.post("/api/api-keys/", json={"name": "other-checkpoint-client"})
    assert other.status_code == 200, other.text
    response = await async_client.post(
        PATHS[0],
        headers={**headers, "authorization": "Bearer " + other.json()["key"]},
        json={"model": MODEL, "input": [checkpoint()], "stream": False},
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "compaction_history_unavailable"
    assert not captured


async def test_generic_source_materializes_checkpoint_without_source_continuation(async_client, recovery_env):
    headers, _, _, _, _ = recovery_env
    compact = await async_client.post(
        PATHS[0] + "/compact",
        headers=headers,
        json={
            "model": "gpt-5.1",
            "instructions": "Keep instructions",
            "input": history(),
        },
    )
    assert compact.status_code == 200, compact.text
    captured = []

    async def handler(request):
        captured.append(await request.json())
        return web.json_response(
            {
                "id": "resp_generic",
                "object": "response",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 10, "output_tokens": 1, "total_tokens": 11},
            }
        )

    async with stub_source_upstreams() as start:
        base_url = await start(handler)
        await _create_model_source(
            async_client, name="checkpoint-generic", model="generic-model", base_url=base_url, supports_responses=True
        )
        response = await async_client.post(
            PATHS[0],
            headers=headers,
            json={
                "model": "generic-model",
                "input": [checkpoint(), {"role": "user", "content": "Continue"}],
                "stream": False,
            },
        )
        assert response.status_code == 200, response.text
    assert len(captured) == 1
    wire = json.dumps(captured[0])
    assert "PRIVATE" not in wire and "encrypted_content" not in wire
    assert "Important tool evidence" in wire and "Original decision" in wire


async def test_failed_native_compaction_does_not_publish_record(async_client, recovery_env, monkeypatch):
    from app.core.clients.proxy import ProxyResponseError
    from app.core.errors import openai_error

    headers, _, captured, _, directory = recovery_env

    async def refuse(*args, **kwargs):
        raise ProxyResponseError(400, openai_error("invalid_request_error", "Native compact refused"))

    monkeypatch.setattr(proxy_service, "core_compact_responses", refuse)
    compact = await async_client.post(
        PATHS[0] + "/compact",
        headers=headers,
        json={
            "model": "gpt-5.1",
            "instructions": "Keep instructions",
            "input": history(),
        },
    )
    assert compact.status_code == 400, compact.text
    assert not list(directory.glob("*.replay"))
    assert not captured
