import asyncio
import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from pydantic import JsonValue

from app.core.config.settings import get_settings
from app.core.crypto import TokenEncryptor
from app.modules.claude.client import ClaudeClient
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.schemas import CatalogModel, UsageSnapshot
from app.modules.proxy.replay_store import HTTPFallbackReplayStore, ReplayScope
from tests.integration.test_claude_accounts import import_body, install_profile_stub
from tests.integration.test_claude_inference import install_upstream
from tests.integration.test_claude_routing import ADAPTIVE_XHIGH
from tests.unit.test_claude_provider_history import history

pytestmark = pytest.mark.integration
MODEL = "anthropic/claude-opus-5-5"
HEADERS = {"session_id": "provider-switch"}


@pytest.fixture
async def opus_pool(async_client, monkeypatch):
    install_profile_stub(monkeypatch)
    monkeypatch.setattr(
        ClaudeClient,
        "catalog",
        AsyncMock(
            return_value=[CatalogModel(id="claude-opus-5-5", display_name="Opus 5.5", capabilities=ADAPTIVE_XHIGH)]
        ),
    )
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    response = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert response.status_code == 200, response.text
    source_id = response.json()["id"]
    refreshed = await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    assert refreshed.status_code == 200, refreshed.text
    selected = await async_client.patch(
        f"/api/claude-accounts/{source_id}", json={"selections": [{"model": "claude-opus-5-5"}]}
    )
    assert selected.status_code == 200, selected.text
    return source_id


def payload(**kwargs):
    return {
        **history(**kwargs),
        "model": MODEL,
        "instructions": "Continue with the full context",
        "reasoning": {"effort": "medium"},
        "stream": False,
    }


def assert_portable(body, *, readable=True, reasoning=True):
    wire = json.dumps(body)
    if readable:
        assert "Sol context" in wire and "Distinct raw context" in wire
    else:
        assert "Sol context" not in wire and "Distinct raw context" not in wire
    assert "Original request" in wire and "Continue on Opus" in wire
    assert "gAAAA" not in wire and "rs_native" not in wire
    if reasoning:
        assert body["thinking"]["type"] == "adaptive"
        assert body["output_config"]["effort"] == "medium"
    else:
        assert "thinking" not in body
    blocks = [block for message in body["messages"] for block in message["content"]]
    assert not any(block["type"] in {"thinking", "redacted_thinking"} for block in blocks)
    assert [block["id"] for block in blocks if block["type"] == "tool_use"] == ["call_native"]
    assert [block["tool_use_id"] for block in blocks if block["type"] == "tool_result"] == ["call_native"]
    result = next(block for block in blocks if block["type"] == "tool_result")
    assert result["content"] == [{"type": "text", "text": "result"}]


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("readable", [False, True])
async def test_sol_to_opus_http_preserves_readable_history_and_retained_state(
    async_client, opus_pool, monkeypatch, path, stream, readable
):
    captured, _ = install_upstream(monkeypatch)
    original = payload() if readable else payload(summary=None, content=None)
    original["stream"] = stream
    untouched = deepcopy(original)
    response = await async_client.post(path, headers=HEADERS, json=original)
    assert response.status_code == 200, response.text
    assert_portable(captured[0][2], readable=readable)
    assert original == untouched
    if stream:
        events = [
            json.loads(line[6:])
            for line in response.text.splitlines()
            if line.startswith("data: ") and line[6:] != "[DONE]"
        ]
        completed = next(event["response"] for event in events if event["type"] == "response.completed")
    else:
        completed = response.json()
    store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
    retained = await store.load(ReplayScope(None, HEADERS["session_id"]), completed["id"])
    assert retained is not None
    assert retained.expand([])[: len(original["input"])] == original["input"]
    followup = await async_client.post(
        path,
        headers=HEADERS,
        json={"model": MODEL, "previous_response_id": completed["id"], "input": "Another turn", "stream": False},
    )
    assert followup.status_code == 200, followup.text
    assert_portable(captured[1][2], readable=readable, reasoning=False)
    next_retained = await store.load(ReplayScope(None, HEADERS["session_id"]), followup.json()["id"])
    assert next_retained is not None
    assert next_retained.expand([])[: len(original["input"])] == original["input"]


@pytest.mark.parametrize("case", ["active", "tampered", "fork"])
async def test_nonportable_and_unauthenticated_history_fails_before_account_selection(
    async_client, opus_pool, monkeypatch, case
):
    from app.modules.claude import inference

    captured, _ = install_upstream(monkeypatch)
    selection = AsyncMock(wraps=inference.select_account)
    monkeypatch.setattr(inference, "select_account", selection)
    request = payload()
    code = "nonportable_provider_history"
    if case == "active":
        request = payload(completed=False)
    elif case in {"tampered", "fork"}:
        code = "invalid_provider_history"
        request["input"][1]["encrypted_content"] = (
            "claude-v1.invalid"
            if case == "tampered"
            else ClaudeOpaqueState(TokenEncryptor()).encode(
                OpaqueScope(opus_pool, MODEL, "anonymous", "parent-conversation"),
                {"type": "thinking", "thinking": "", "signature": "parent-signed"},
            )
        )
    response = await async_client.post("/backend-api/codex/responses", headers=HEADERS, json=request)
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["param"] == "input[1]"
    assert error["message"] != "Invalid request payload"
    assert not captured
    selection.assert_not_awaited()


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
@pytest.mark.parametrize("readable", [False, True])
async def test_complete_compaction_still_refuses_foreign_ciphertext(
    async_client, opus_pool, monkeypatch, path, readable
):
    from app.modules.claude import inference

    captured, _ = install_upstream(monkeypatch)
    selection = AsyncMock(wraps=inference.select_account)
    monkeypatch.setattr(inference, "select_account", selection)
    request = payload() if readable else payload(summary=None, content=None)
    response = await async_client.post(path, headers=HEADERS, json=request)
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == "nonportable_provider_history"
    assert error["param"] == "input[1]"
    assert "Complete compaction" in error["message"]
    assert not captured
    selection.assert_not_awaited()


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
async def test_plaintext_compaction_preserves_all_reasoning(async_client, opus_pool, monkeypatch, path):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(path, headers=HEADERS, json=payload(token=None))
    assert response.status_code == 200, response.text
    assert response.json()["object"] == "response.compaction"
    assert "Sol context" in json.dumps(captured[0][2])
    assert "Distinct raw context" in json.dumps(captured[0][2])
    assert "result" in json.dumps(captured[0][2])


async def test_opus_sol_opus_preserves_original_empty_display_signed_blocks(async_client, opus_pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    signed: dict[str, JsonValue] = {"type": "thinking", "thinking": "", "signature": "original-signed-state"}
    token = ClaudeOpaqueState(TokenEncryptor()).encode(
        OpaqueScope(opus_pool, MODEL, "anonymous", HEADERS["session_id"]), signed
    )
    request = payload()
    request["input"].insert(0, {"type": "reasoning", "summary": [], "encrypted_content": token})
    response = await async_client.post("/backend-api/codex/responses", headers=HEADERS, json=request)
    assert response.status_code == 200, response.text
    blocks = [block for message in captured[0][2]["messages"] for block in message["content"]]
    assert signed in blocks
    assert "Sol context" in json.dumps(blocks)
    assert "gAAAA" not in json.dumps(blocks)


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("readable", [False, True])
async def test_sol_to_opus_websocket_projects_or_returns_specific_error(
    async_client, opus_pool, monkeypatch, path, active, readable
):
    captured, _ = install_upstream(monkeypatch)
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
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
    request = payload(completed=not active) if readable else payload(completed=not active, summary=None, content=None)
    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        await incoming.put(
            {
                "type": "websocket.receive",
                "text": json.dumps({**request, "type": "response.create", "stream": True}),
            }
        )
        while True:
            frame = await asyncio.wait_for(outgoing.get(), 5)
            event = json.loads(frame["text"])
            if event["type"] == "error":
                assert active, event
                assert event["error"]["code"] == "nonportable_provider_history"
                assert event["error"]["param"] == "input[1]"
                assert not captured
                break
            if event["type"] == "response.completed":
                assert not active
                assert_portable(captured[0][2], readable=readable)
                store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
                retained = await store.load(ReplayScope(None, HEADERS["session_id"]), event["response"]["id"])
                assert retained is not None
                assert retained.expand([])[: len(request["input"])] == request["input"]
                break
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
