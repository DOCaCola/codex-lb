"""Complete source summarization at the real HTTP and websocket boundaries."""

import asyncio
import json
from contextlib import asynccontextmanager

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
FOREIGN_TOKEN = "gAAAA_sol_private_state"


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


def switched_history(ending: str) -> list[JsonValue]:
    """Sol history (readable and opaque-only reasoning) continued on Claude."""
    items: list[JsonValue] = [
        {"role": "user", "content": "Original Sol task"},
        {
            "type": "reasoning",
            "id": "rs_sol",
            "summary": [{"type": "summary_text", "text": "Sol readable context"}],
            "encrypted_content": FOREIGN_TOKEN,
        },
        {"type": "function_call", "name": "inspect", "call_id": "call_sol", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_sol", "output": "Sol tool evidence"},
        {"type": "reasoning", "id": "rs_sol_opaque", "summary": [], "encrypted_content": FOREIGN_TOKEN},
    ]
    if ending == "assistant":
        items.append({"type": "message", "role": "assistant", "content": "Sol final answer"})
    elif ending == "user":
        items.append({"type": "message", "role": "assistant", "content": "Sol final answer"})
        items.append({"role": "user", "content": "Continue on Opus"})
        items.append({"type": "message", "role": "assistant", "content": "Opus answer"})
    return items


TOOLS: list[JsonValue] = [
    {"type": "function", "name": "inspect", "parameters": {"type": "object", "properties": {}}},
    {"type": "custom", "name": "apply_patch", "description": "Edit files"},
]


def without_cache_markers(value: JsonValue) -> JsonValue:
    if isinstance(value, list):
        return [without_cache_markers(item) for item in value]
    if isinstance(value, dict):
        return {key: without_cache_markers(item) for key, item in value.items() if key != "cache_control"}
    return value


def assert_reuses_turn_prefix(turn: dict[str, JsonValue], compaction: dict[str, JsonValue]) -> None:
    """Claude caches tools -> system -> messages; compaction must extend the turn's prefix."""
    for field in ("tools", "tool_choice", "system"):
        assert without_cache_markers(compaction[field]) == without_cache_markers(turn[field])
    turn_messages = without_cache_markers(turn["messages"])
    compaction_messages = without_cache_markers(compaction["messages"])
    assert isinstance(turn_messages, list) and isinstance(compaction_messages, list)
    assert compaction_messages[: len(turn_messages)] == turn_messages
    serialized = json.dumps(compaction_messages[-1])
    assert "CONTEXT CHECKPOINT COMPACTION" in serialized and "Do not call any tools" in serialized


@asynccontextmanager
async def websocket_session(async_client, path, session_id):
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"user-agent", b"codex_cli_rs/0.157.0"), (b"session_id", session_id.encode())],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))

    async def turn(payload, *, allow_error=False):
        await incoming.put(
            {"type": "websocket.receive", "text": json.dumps({"type": "response.create", "model": MODEL, **payload})}
        )
        while True:
            frame = await asyncio.wait_for(outgoing.get(), 10)
            assert frame["type"] == "websocket.send", frame
            event = json.loads(frame["text"])
            if event["type"] in ("error", "response.failed"):
                assert allow_error, event
                return event
            if event["type"] == "response.completed":
                return event["response"]

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
    async with websocket_session(async_client, path, "complete-source-ws") as turn:
        first = await turn({"input": complete_history()})
        compact = await turn({"previous_response_id": first["id"], "input": [{"type": "compaction_trigger"}]})
        assert_complete_messages(captured[-1][2])
        assert [item["type"] for item in compact["output"]] == ["compaction"]
        await turn({"input": [*compact["output"], {"role": "user", "content": "Resume the task"}]})
        assert "Hello from Claude" in json.dumps(captured[-1][2]["messages"])
    assert len(closed) == len(captured) == 3


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
async def test_claude_compact_endpoint_reuses_conversation_tool_prefix(async_client, pool, monkeypatch, path):
    captured, _ = install_upstream(monkeypatch)
    headers = {"session_id": "cache-preserving-compact"}
    body = {"model": MODEL, "instructions": "Keep the task context", "tools": TOOLS, "parallel_tool_calls": True}
    first = await async_client.post("/v1/responses", headers=headers, json={**body, "input": complete_history()})
    assert first.status_code == 200, first.text
    response = await async_client.post(
        path,
        headers=headers,
        json={**body, "input": [], "previous_response_id": first.json()["id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["output"][0]["type"] == "compaction"
    assert len(captured) == 2
    assert_reuses_turn_prefix(captured[0][2], captured[1][2])


@pytest.mark.parametrize("path", ["/backend-api/codex/responses", "/v1/responses"])
async def test_websocket_compaction_trigger_reuses_conversation_tool_prefix(async_client, pool, monkeypatch, path):
    captured, _ = install_upstream(monkeypatch)
    declarations = {"tools": TOOLS, "tool_choice": "auto", "parallel_tool_calls": True}
    async with websocket_session(async_client, path, "cache-preserving-ws") as turn:
        first = await turn({**declarations, "input": complete_history()})
        compact = await turn(
            {**declarations, "previous_response_id": first["id"], "input": [{"type": "compaction_trigger"}]}
        )
    assert [item["type"] for item in compact["output"]] == ["compaction"]
    assert len(captured) == 2
    assert_reuses_turn_prefix(captured[0][2], captured[1][2])


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
async def test_claude_compaction_tool_call_fails_without_checkpoint(async_client, pool, monkeypatch, path):
    from starlette.requests import Request

    from app.modules.claude.protocol import ToolIdentity
    from app.modules.model_sources.continuation import SourceContinuation

    captured, _ = install_upstream(monkeypatch)
    headers = {"session_id": "compaction-tool-call"}
    body = {"model": MODEL, "instructions": "Keep the task context", "tools": TOOLS}
    first = await async_client.post("/v1/responses", headers=headers, json={**body, "input": complete_history()})
    assert first.status_code == 200, first.text
    continuation = SourceContinuation(
        Request({"type": "http", "headers": [(b"session_id", headers["session_id"].encode())]}), None, captured[0][0]
    )
    before = await continuation.store.load(continuation.scope, first.json()["id"])
    assert before is not None
    wire_name = ToolIdentity("inspect", None, False).wire_name
    called, _ = install_upstream(
        monkeypatch,
        stop="tool_use",
        message_id="msg_tool_compact",
        content=[
            {"type": "text", "text": "Let me look first"},
            {"type": "tool_use", "id": "toolu_compact", "name": wire_name, "input": {}},
        ],
    )
    response = await async_client.post(
        path, headers=headers, json={**body, "input": [], "previous_response_id": first.json()["id"]}
    )
    assert response.status_code == 502, response.text
    assert response.json()["error"]["code"] == "model_source_compaction_invalid"
    assert "output" not in response.json()
    assert len(called) == 1
    assert await continuation.store.load(continuation.scope, first.json()["id"]) == before


def assert_portable_switch_summary(payload: dict[str, JsonValue]) -> None:
    serialized = json.dumps(payload["messages"])
    assert "Sol readable context" in serialized and "Sol tool evidence" in serialized
    assert "CONTEXT CHECKPOINT COMPACTION" in serialized
    assert FOREIGN_TOKEN not in serialized and "rs_sol" not in serialized
    assert '"thinking"' not in serialized


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
@pytest.mark.parametrize("ending", ["assistant", "user"])
async def test_compaction_after_provider_switch_projects_closed_foreign_turns(
    async_client, pool, monkeypatch, path, ending
):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        path, json={"model": MODEL, "instructions": "summarize", "input": switched_history(ending)}
    )
    assert response.status_code == 200, response.text
    assert len(captured) == 1
    assert_portable_switch_summary(captured[0][2])
    assert response.json()["output"][0]["type"] == "compaction"


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
async def test_compaction_refuses_open_foreign_tool_loop_without_dispatch(async_client, pool, monkeypatch, path):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        path, json={"model": MODEL, "instructions": "summarize", "input": switched_history("open")[:4]}
    )
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert (error["code"], error["param"]) == ("nonportable_provider_history", "input[1]")
    assert error["message"].startswith("Active reasoning continuation")
    assert not captured


@pytest.mark.parametrize("path", ["/backend-api/codex/responses", "/v1/responses"])
@pytest.mark.parametrize("ending", ["assistant", "open"])
async def test_websocket_compaction_trigger_after_provider_switch(async_client, pool, monkeypatch, path, ending):
    captured, _ = install_upstream(monkeypatch)
    history = switched_history(ending) if ending == "assistant" else switched_history(ending)[:4]
    async with websocket_session(async_client, path, f"switch-compact-{ending}") as turn:
        result = await turn({"input": [*history, {"type": "compaction_trigger"}]}, allow_error=ending == "open")
    if ending == "assistant":
        assert [item["type"] for item in result["output"]] == ["compaction"]
        assert len(captured) == 1
        assert_portable_switch_summary(captured[0][2])
    else:
        assert "nonportable_provider_history" in json.dumps(result)
        assert not captured


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
@pytest.mark.parametrize(
    "state", ["available", "paused", "model_switch", "signature_rejected", "search", "search_paused"]
)
async def test_compaction_preserves_signed_history_on_any_route(async_client, pool, monkeypatch, path, state):
    from app.db.models import ModelSource
    from app.db.session import SessionLocal
    from tests.unit.test_claude_search import search_content

    signed = {"type": "thinking", "thinking": "IMPORTANT SIGNED HISTORY", "signature": "original-signature"}
    readable = {"type": "text", "text": "IMPORTANT SIGNED HISTORY"}
    search = state.startswith("search")
    captured, _ = install_upstream(
        monkeypatch,
        content=search_content() if search else [signed, {"type": "text", "text": "answer"}],
    )
    headers = {"session_id": "signed-complete-compact"}
    first_body = {"model": MODEL, "input": "Original context"}
    if search:
        first_body["tools"] = [{"type": "web_search"}]
    first = await async_client.post("/v1/responses", headers=headers, json=first_body)
    assert first.status_code == 200, first.text
    owner = captured[0][0]
    if state.endswith("paused"):
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
    if state == "search_paused":
        assert response.status_code == 503, response.text
        assert not later
        assert "output" not in response.json()
        return
    assert response.status_code == 200, response.text
    assert len(later) == (2 if state == "signature_rejected" else 1)
    # A model switch has no replayable signature, so routing may pick any account.
    expected = {"paused": set(pool) - {owner}, "model_switch": set(pool)}.get(state, {owner})
    assert len({request[0] for request in later}) == 1
    assert {request[0] for request in later} <= expected
    sent = [[block for message in request[2]["messages"] for block in message["content"]] for request in later]
    if search:
        assert any(block.get("type") == "web_search_tool_result" for block in sent[0])
    elif state == "available":
        assert signed in sent[0]
    else:
        # Another route, or a rejected signature: the summarizer reads the thinking.
        assert readable in sent[-1]
        assert signed not in sent[-1]
        if state == "signature_rejected":
            assert signed in sent[0]
    assert "CONTEXT CHECKPOINT COMPACTION" in json.dumps(sent[-1])


@pytest.mark.parametrize("path", ["/backend-api/codex/responses", "/v1/responses"])
async def test_websocket_compaction_trigger_reads_signed_history_after_model_switch(
    async_client, pool, monkeypatch, path
):
    signed = {"type": "thinking", "thinking": "IMPORTANT SIGNED HISTORY", "signature": "original-signature"}
    captured, _ = install_upstream(monkeypatch, content=[signed, {"type": "text", "text": "answer"}])
    async with websocket_session(async_client, path, "signed-switch-ws") as turn:
        first = await turn({"input": "Original context"})
        compact = await turn(
            {
                "model": "anthropic/claude-sonnet-5",
                "previous_response_id": first["id"],
                "input": [{"type": "compaction_trigger"}],
            }
        )
    assert [item["type"] for item in compact["output"]] == ["compaction"]
    assert len(captured) == 2
    blocks = [block for message in captured[1][2]["messages"] for block in message["content"]]
    assert {"type": "text", "text": "IMPORTANT SIGNED HISTORY"} in blocks
    assert signed not in blocks


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
