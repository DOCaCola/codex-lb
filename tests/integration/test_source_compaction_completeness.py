"""Complete source summarization at the real HTTP and websocket boundaries."""

import asyncio
import json

import pytest
from pydantic import JsonValue

from app.core.openai.compaction import decode_codex_lb_compaction_summary
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration import test_claude_routing as routing_fixtures
from tests.integration.test_claude_inference import install_upstream

MODEL = routing_fixtures.MODEL
pool = routing_fixtures.pool

pytestmark = pytest.mark.integration

IMAGE = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
)
TOOL_OUTPUT = "MIDDLE: critical tool evidence\n" + "x" * 600_000


def complete_history() -> list[JsonValue]:
    return [
        {"role": "user", "content": "EARLIEST: preserve the original decision"},
        {"role": "assistant", "content": "I will inspect the evidence"},
        {"type": "function_call", "name": "inspect", "namespace": "functions", "call_id": "call_1", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": TOOL_OUTPUT},
        {"role": "assistant", "content": "Evidence inspected"},
        {"role": "user", "content": [{"type": "input_image", "image_url": IMAGE}]},
        {"role": "assistant", "content": "The attachment is still relevant"},
        {"role": "user", "content": "LATEST: preserve the final constraint"},
    ]


def assert_complete_messages(payload: dict[str, JsonValue]) -> None:
    messages = payload["messages"]
    assert isinstance(messages, list)
    serialized = json.dumps(messages)
    assert "EARLIEST: preserve the original decision" in serialized
    assert TOOL_OUTPUT in serialized.replace("\\n", "\n")
    assert "LATEST: preserve the final constraint" in serialized
    assert IMAGE.split(",", 1)[1] in serialized
    assert "[compact trim]" not in serialized
    assert "[image omitted for compaction]" not in serialized
    assert "CONTEXT CHECKPOINT COMPACTION" in serialized
    assert "tools" not in payload
    assert "tool_choice" not in payload


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
@pytest.mark.parametrize("retained", [False, True])
async def test_complete_claude_compact_history_and_continuation(async_client, pool, monkeypatch, path, retained):
    captured, closed = install_upstream(monkeypatch)
    headers = {"session_id": "complete-source-compact"}
    history = complete_history()
    body = {"model": MODEL, "instructions": "Keep the task context", "input": history}
    if retained:
        first = await async_client.post("/v1/responses", headers=headers, json=body)
        assert first.status_code == 200, first.text
        body = {
            **body,
            "input": [{"role": "user", "content": "compact now"}],
            "previous_response_id": first.json()["id"],
        }
    response = await async_client.post(path, headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert_complete_messages(captured[-1][2])
    checkpoint = response.json()["output"][0]
    assert checkpoint["type"] == "compaction"
    assert decode_codex_lb_compaction_summary(checkpoint["encrypted_content"]) == "Hello from Claude"
    followup = await async_client.post(
        "/v1/responses",
        headers=headers,
        json={"model": MODEL, "input": [checkpoint, {"role": "user", "content": "Continue"}]},
    )
    assert followup.status_code == 200, followup.text
    assert "Hello from Claude" in json.dumps(captured[-1][2]["messages"])
    assert len(closed) == len(captured)


@pytest.mark.parametrize("path", ["/backend-api/codex/responses", "/v1/responses"])
async def test_websocket_compact_materializes_complete_history(async_client, pool, monkeypatch, path):
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
        "headers": [(b"user-agent", b"codex_cli_rs/0.157.0"), (b"session_id", b"complete-source-ws")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))

    async def turn(payload):
        await incoming.put(
            {"type": "websocket.receive", "text": json.dumps({"type": "response.create", "model": MODEL, **payload})}
        )
        while True:
            frame = await asyncio.wait_for(outgoing.get(), 10)
            assert frame["type"] == "websocket.send", frame
            event = json.loads(frame["text"])
            assert event["type"] not in ("error", "response.failed"), event
            if event["type"] == "response.completed":
                return event["response"]

    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        first = await turn({"input": complete_history()})
        compact = await turn({"previous_response_id": first["id"], "input": [{"type": "compaction_trigger"}]})
        assert_complete_messages(captured[-1][2])
        assert [item["type"] for item in compact["output"]] == ["compaction"]
        await turn({"input": [*compact["output"], {"role": "user", "content": "Resume the task"}]})
        assert "Hello from Claude" in json.dumps(captured[-1][2]["messages"])
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert len(closed) == len(captured) == 3


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
@pytest.mark.parametrize("failure", ["capacity", "incomplete"])
async def test_compact_failure_does_not_replace_original_history(async_client, pool, monkeypatch, path, failure):
    from starlette.requests import Request

    from app.modules.claude import transport
    from app.modules.model_sources.continuation import SourceContinuation

    captured, _ = install_upstream(monkeypatch)
    headers = {"session_id": "failed-source-compact"}
    first = await async_client.post(
        "/v1/responses", headers=headers, json={"model": MODEL, "input": complete_history()}
    )
    assert first.status_code == 200, first.text
    continuation = SourceContinuation(
        Request({"type": "http", "headers": [(b"session_id", headers["session_id"].encode())]}), None, captured[0][0]
    )
    before = await continuation.store.load(continuation.scope, first.json()["id"])
    assert before is not None
    if failure == "capacity":
        refused = []

        async def reject(source, path, payload, **kwargs):
            refused.append(payload)
            raise ModelSourceForwardingError(
                status_code=400,
                upstream_status_code=400,
                payload={"error": {"type": "invalid_request_error", "message": "prompt is too long"}},
            )

        monkeypatch.setattr(transport, "_open_source_stream", reject)
    else:
        incomplete, closed = install_upstream(monkeypatch, stop="max_tokens", message_id="msg_incomplete_compact")
    response = await async_client.post(
        path,
        headers=headers,
        json={"model": MODEL, "instructions": "compact", "input": [], "previous_response_id": first.json()["id"]},
    )
    assert response.status_code == (400 if failure == "capacity" else 502), response.text
    assert "output" not in response.json()
    if failure == "capacity":
        assert len(refused) == 1
        assert_complete_messages(refused[0])
    else:
        assert len(incomplete) == len(closed) == 1
        assert_complete_messages(incomplete[0][2])
    after = await continuation.store.load(continuation.scope, first.json()["id"])
    assert after == before
    # A failed compaction leaves the original anchor usable, not just present.
    continued, _ = install_upstream(monkeypatch)
    retry = await async_client.post(
        "/v1/responses",
        headers=headers,
        json={"model": MODEL, "previous_response_id": first.json()["id"], "input": "Continue without compacting"},
    )
    assert retry.status_code == 200, retry.text
    assert TOOL_OUTPUT in json.dumps(continued[0][2]["messages"]).replace("\\n", "\n")


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
@pytest.mark.parametrize("state", ["available", "paused", "model_switch", "signature_rejected", "search"])
async def test_compaction_keeps_signed_history_owned_or_returns_error(async_client, pool, monkeypatch, path, state):
    from app.db.models import ModelSource
    from app.db.session import SessionLocal
    from tests.unit.test_claude_search import search_content

    signed = {"type": "thinking", "thinking": "IMPORTANT SIGNED HISTORY", "signature": "original-signature"}
    captured, _ = install_upstream(
        monkeypatch,
        content=search_content() if state == "search" else [signed, {"type": "text", "text": "answer"}],
    )
    headers = {"session_id": "signed-complete-compact"}
    first_body = {"model": MODEL, "input": "Original context"}
    if state == "search":
        first_body["tools"] = [{"type": "web_search"}]
    first = await async_client.post("/v1/responses", headers=headers, json=first_body)
    assert first.status_code == 200, first.text
    owner = captured[0][0]
    if state == "paused":
        async with SessionLocal() as session:
            source = await session.get(ModelSource, owner)
            assert source is not None
            source.is_enabled = False
            await session.commit()
    later, _ = install_upstream(monkeypatch, rejections=1 if state == "signature_rejected" else 0)
    response = await async_client.post(
        path,
        headers=headers,
        json={
            "model": "anthropic/claude-sonnet-5" if state == "model_switch" else MODEL,
            "instructions": "Summarize all context",
            "input": [{"role": "user", "content": "compact now"}],
            "previous_response_id": first.json()["id"],
        },
    )
    if state in {"paused", "model_switch"}:
        assert response.status_code == (503 if state == "paused" else 400), response.text
        assert not later
        assert "output" not in response.json()
    else:
        assert len(later) == 1
        assert later[0][0] == owner
        blocks = [block for message in later[0][2]["messages"] for block in message["content"]]
        if state == "search":
            assert any(block.get("type") == "web_search_tool_result" for block in blocks)
        else:
            assert signed in blocks
        assert response.status_code == (400 if state == "signature_rejected" else 200), response.text
        if state == "signature_rejected":
            assert "output" not in response.json()


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
async def test_compaction_does_not_fabricate_pending_tool_result(async_client, pool, monkeypatch, path):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        path,
        json={
            "model": MODEL,
            "instructions": "summarize",
            "input": [
                {"role": "user", "content": "original task"},
                {"type": "function_call", "name": "inspect", "call_id": "call_pending", "arguments": "{}"},
            ],
        },
    )
    assert response.status_code == 400, response.text
    assert not captured
    assert "output" not in response.json()


@pytest.mark.parametrize("failure", ["capacity", "incomplete"])
async def test_compaction_failure_settles_usage_and_releases_admission(async_client, pool, monkeypatch, failure):
    from sqlalchemy import select

    from app.db.models import ApiKeyUsageReservation, RequestLog
    from app.db.session import SessionLocal
    from app.modules.claude import transport
    from app.modules.proxy.source_admission import get_source_bulkhead
    from tests.integration.model_source_helpers import _enable_api_key_auth

    await _enable_api_key_auth(async_client)
    created = await async_client.post(
        "/api/api-keys/",
        json={
            "name": "failed-compact-key",
            "assignedSourceIds": [pool[0]],
            "limits": [{"limitType": "total_tokens", "limitWindow": "weekly", "maxValue": 1_000_000}],
        },
    )
    assert created.status_code == 200, created.text
    key = created.json()
    if failure == "capacity":

        async def reject(*args, **kwargs):
            raise ModelSourceForwardingError(
                status_code=400,
                upstream_status_code=400,
                payload={"error": {"type": "invalid_request_error", "message": "prompt is too long"}},
            )

        monkeypatch.setattr(transport, "_open_source_stream", reject)
    else:
        install_upstream(monkeypatch, stop="max_tokens")
    response = await async_client.post(
        "/v1/responses/compact",
        headers={"Authorization": f"Bearer {key['key']}"},
        json={"model": MODEL, "instructions": "summarize", "input": complete_history()},
    )
    assert response.status_code == (400 if failure == "capacity" else 502), response.text
    assert get_source_bulkhead().in_flight(pool[0]) == 0
    async with SessionLocal() as session:
        reservation = (
            await session.scalars(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.api_key_id == key["id"]))
        ).one()
        assert reservation.status == ("released" if failure == "capacity" else "finalized")
        if failure == "incomplete":
            assert reservation.input_tokens == 10 and reservation.output_tokens == 7
        rows = list(await session.scalars(select(RequestLog).where(RequestLog.api_key_id == key["id"])))
        assert len(rows) == 1
        assert rows[0].model_source_id == pool[0]
