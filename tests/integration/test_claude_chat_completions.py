"""Public Chat route regressions for the Claude Responses adapter."""

import json
from contextlib import AsyncExitStack
from types import SimpleNamespace

import pytest

from tests.integration import test_claude_routing as routing_fixtures
from tests.integration.model_source_helpers import _create_model_source, _enable_api_key_auth
from tests.integration.test_claude_inference import install_upstream
from tests.integration.test_model_source_dispatch import _create_limited_key, _reservations

MODEL = routing_fixtures.MODEL
pool = routing_fixtures.pool

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("stream", [False, True])
async def test_claude_chat_text_uses_owned_responses_dispatch(async_client, pool, monkeypatch, stream):
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], "stream": stream},
    )
    assert response.status_code == 200, response.text
    assert closed == [captured[0][0]]
    assert captured[0][1].startswith("/v1/messages")
    assert captured[0][2]["model"] == "claude-opus-5"
    if stream:
        assert '"object":"chat.completion.chunk"' in response.text
        assert '"finish_reason":"stop"' in response.text
        assert response.text.rstrip().endswith("data: [DONE]")
    else:
        completion = response.json()
        assert completion["object"] == "chat.completion"
        assert completion["choices"][0]["message"]["content"] == "Hello from Claude"
        assert completion["usage"]["total_tokens"] == 17


@pytest.mark.parametrize("stream", [False, True])
async def test_claude_chat_limit_and_stops_reach_messages(async_client, pool, monkeypatch, stream):
    captured, _ = install_upstream(monkeypatch, stop="max_tokens")
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
            "max_completion_tokens": 17,
            "stop": ["END"],
            "stream": stream,
        },
    )
    assert response.status_code == 200, response.text
    assert captured[0][2]["max_tokens"] == 17
    assert captured[0][2]["stop_sequences"] == ["END"]
    if stream:
        assert '"finish_reason":"length"' in response.text
    else:
        assert response.json()["choices"][0]["finish_reason"] == "length"


@pytest.mark.parametrize("stream", [False, True])
async def test_claude_chat_pause_turn_is_error(async_client, pool, monkeypatch, stream):
    install_upstream(monkeypatch, stop="pause_turn")
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], "stream": stream},
    )
    if stream:
        assert '"code":"upstream_response_incomplete"' in response.text
        assert '"finish_reason":"stop"' not in response.text
    else:
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "upstream_response_incomplete"


@pytest.mark.parametrize(
    "control",
    [
        {"seed": 9},
        {"seed": 0},
        {"presence_penalty": 1},
        {"logprobs": True},
        {"store": True},
        {"thinking": {"type": "enabled", "budget_tokens": 500}},
        {"response_format": {"type": "json_object"}},
        {"unknown_control": "must not disappear"},
    ],
)
async def test_claude_chat_rejects_unsupported_controls_before_send(async_client, pool, monkeypatch, control):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], **control},
    )
    assert response.status_code == 400
    assert response.json()["error"]["param"] == next(iter(control))
    assert not captured


@pytest.mark.parametrize("sampling", [{"temperature": 0.2}, {"top_p": 0.9}])
async def test_claude_chat_rejects_thinking_sampling_conflicts(async_client, pool, monkeypatch, sampling):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "reasoning_effort": "medium",
            **sampling,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["param"] == next(iter(sampling))
    assert captured == []


async def test_claude_chat_tool_followup_reconstructs_portable_history(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    tool = {
        "type": "function",
        "function": {
            "name": "lookup",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
        },
    }
    captured, _ = install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {"city": "Berlin"},
            }
        ],
    )
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": MODEL, "messages": [{"role": "user", "content": "Weather?"}], "tools": [tool]},
    )
    assert response.status_code == 200, response.text
    call = response.json()["choices"][0]["message"]["tool_calls"][0]
    assert response.json()["choices"][0]["finish_reason"] == "tool_calls"
    assert call["id"] == "tool_1"
    assert call["function"]["name"] == "lookup"
    assert json.loads(call["function"]["arguments"]) == {"city": "Berlin"}
    followup = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Weather?"},
                {"role": "assistant", "content": None, "tool_calls": [call]},
                {"role": "tool", "tool_call_id": call["id"], "content": "Sunny"},
            ],
            "tools": [tool],
        },
    )
    assert followup.status_code == 200, followup.text
    sent = captured[1][2]["messages"]
    assert not any(block.get("type") in {"tool_use", "tool_result"} for message in sent for block in message["content"])
    assert "lookup" in json.dumps(sent)
    assert "Sunny" in json.dumps(sent)


async def test_claude_chat_reasoning_is_visible_without_replaying_a_signature(async_client, pool, monkeypatch):
    from sqlalchemy import select

    from app.db.models import RequestLog
    from app.db.session import SessionLocal

    install_upstream(
        monkeypatch,
        content=[
            {"type": "thinking", "thinking": "Check the premise", "signature": "signed-by-claude"},
            {"type": "text", "text": "Answer"},
        ],
    )
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "reasoning_effort": "medium",
        },
    )
    assert response.status_code == 200, response.text
    message = response.json()["choices"][0]["message"]
    assert message["reasoning_content"] == "Check the premise"
    assert message["content"] == "Answer"
    assert "signed-by-claude" not in response.text
    async with SessionLocal() as session:
        row = (await session.scalars(select(RequestLog).where(RequestLog.model == MODEL))).one()
        assert row.reasoning_effort == "medium"
        assert row.upstream_thinking_mode == "adaptive"
        assert row.upstream_thinking_budget_tokens is None
        assert row.reasoning_tokens is None


async def test_claude_chat_preserves_completed_plaintext_reasoning_as_text(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [
                {"role": "assistant", "content": "Answer", "reasoning_content": "private reasoning"},
                {"role": "user", "content": "Continue"},
            ],
        },
    )
    assert response.status_code == 200
    assert captured
    assert "Visible prior reasoning: private reasoning" in json.dumps(captured[0][2])
    assert "signature" not in json.dumps(captured[0][2])


async def test_claude_chat_allows_reasoning_with_declared_tools(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "reasoning_effort": "high",
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}},
                }
            ],
        },
    )
    assert response.status_code == 200
    assert captured[0][2]["thinking"] == {"type": "adaptive", "display": "summarized"}


async def test_claude_chat_thinking_display_and_inert_controls(async_client, pool, monkeypatch):
    captured, _ = install_upstream(
        monkeypatch,
        content=[
            {"type": "thinking", "thinking": "hidden", "signature": "genuine-signature"},
            {"type": "text", "text": "Answer"},
        ],
    )
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "thinking": {"type": "adaptive", "display": "omitted"},
            "tools": [
                {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}}}
            ],
            "tool_choice": "none",
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "logprobs": False,
            "top_logprobs": 0,
        },
    )
    assert response.status_code == 200, response.text
    assert captured[0][2]["thinking"] == {"type": "adaptive"}
    assert captured[0][2]["tool_choice"] == {"type": "none"}
    assert "reasoning_content" not in response.json()["choices"][0]["message"]


async def test_claude_chat_restores_signed_tool_reasoning_for_same_client(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    await _enable_api_key_auth(async_client)
    key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-signed-replay")
    headers = {"Authorization": f"Bearer {key}"}
    tool = {
        "type": "function",
        "function": {"name": "lookup", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}},
    }
    captured, _ = install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {"type": "thinking", "thinking": "Check the location", "signature": "genuine-signature"},
            {
                "type": "tool_use",
                "id": "tool_signed_1",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {"city": "Berlin"},
            },
            {
                "type": "tool_use",
                "id": "tool_signed_2",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {"city": "Paris"},
            },
        ],
    )
    first = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Weather?"}],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert first.status_code == 200, first.text
    assistant = first.json()["choices"][0]["message"]
    assert assistant["reasoning_content"] == "Check the location"
    followup_messages = [
        {"role": "user", "content": "Weather?"},
        {
            "role": "assistant",
            "content": assistant.get("content"),
            "tool_calls": assistant["tool_calls"],
            "reasoning_content": assistant["reasoning_content"],
        },
        {"role": "tool", "tool_call_id": "tool_signed_1", "content": "Sunny"},
        {"role": "tool", "tool_call_id": "tool_signed_2", "content": "Rainy"},
    ]
    second = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"model": MODEL, "messages": followup_messages, "tools": [tool], "reasoning_effort": "high"},
    )
    assert second.status_code == 200, second.text
    assert captured[1][0] == captured[0][0]
    assert captured[1][2]["messages"][1]["content"][0] == {
        "type": "thinking",
        "thinking": "Check the location",
        "signature": "genuine-signature",
    }
    assert [block["type"] for block in captured[1][2]["messages"][2]["content"]] == ["tool_result", "tool_result"]


async def test_claude_chat_missing_signed_tool_replay_reconstructs(async_client, pool, monkeypatch):
    await _enable_api_key_auth(async_client)
    key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-missing-replay")
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Weather?"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "unknown-call",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "unknown-call", "content": "Sunny"},
            ],
            "reasoning_effort": "high",
        },
    )
    assert response.status_code == 200, response.text
    sent = captured[0][2]
    assert sent["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert "unknown-call" in json.dumps(sent["messages"])
    assert "Sunny" in json.dumps(sent["messages"])
    assert not any(
        block.get("type") in {"tool_use", "tool_result"} for message in sent["messages"] for block in message["content"]
    )


async def test_claude_chat_signed_replay_is_bound_to_api_key(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    await _enable_api_key_auth(async_client)
    first_key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-owner")
    second_key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-other")
    tool = {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}}}
    captured, _ = install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {"type": "redacted_thinking", "data": "genuine-redaction"},
            {
                "type": "tool_use",
                "id": "key_bound_call",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {},
            },
        ],
    )
    first = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {first_key}"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Look up"}],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert first.status_code == 200, first.text
    call = first.json()["choices"][0]["message"]["tool_calls"][0]
    second = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {second_key}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Look up"},
                {"role": "assistant", "content": None, "tool_calls": [call], "reasoning_content": None},
                {"role": "tool", "tool_call_id": call["id"], "content": "Found"},
            ],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert second.status_code == 200, second.text
    assert "genuine-redaction" not in json.dumps(captured[1][2])
    assert "key_bound_call" in json.dumps(captured[1][2])
    same_key = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {first_key}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Look up"},
                {"role": "assistant", "content": None, "tool_calls": [call], "reasoning_content": None},
                {"role": "tool", "tool_call_id": call["id"], "content": "Found"},
            ],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert same_key.status_code == 200, same_key.text
    assert captured[2][2]["messages"][1]["content"][0] == {"type": "redacted_thinking", "data": "genuine-redaction"}


async def test_claude_chat_later_tool_turn_matches_canonical_visible_history(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    await _enable_api_key_auth(async_client)
    key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-later-turn")
    headers = {"Authorization": f"Bearer {key}"}
    tool = {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}}}
    messages = [{"role": "user", "content": "Look up twice"}]
    for index in (1, 2):
        captured, _ = install_upstream(
            monkeypatch,
            stop="tool_use",
            message_id=f"msg_later_{index}",
            content=[
                {"type": "thinking", "thinking": f"step {index}", "signature": f"real-signature-{index}"},
                {
                    "type": "tool_use",
                    "id": f"later_call_{index}",
                    "name": ToolIdentity("lookup", None, False).wire_name,
                    "input": {"step": index},
                },
            ],
        )
        response = await async_client.post(
            "/v1/chat/completions",
            headers=headers,
            json={"model": MODEL, "messages": messages, "tools": [tool], "reasoning_effort": "high"},
        )
        assert response.status_code == 200, response.text
        if index == 2:
            assert "real-signature-1" in json.dumps(captured[0][2])
        assistant = response.json()["choices"][0]["message"]
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": assistant.get("content"),
                    "tool_calls": assistant["tool_calls"],
                    "reasoning_content": assistant.get("reasoning_content"),
                },
                {"role": "tool", "tool_call_id": f"later_call_{index}", "content": f"result {index}"},
            ]
        )
    captured, _ = install_upstream(monkeypatch)
    third = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"model": MODEL, "messages": messages, "tools": [tool], "reasoning_effort": "high"},
    )
    assert third.status_code == 200, third.text
    sent = json.dumps(captured[0][2])
    assert "real-signature-1" in sent, sent
    assert "real-signature-2" in sent, sent
    assert "result 1" in sent and "result 2" in sent


async def test_claude_chat_owner_unavailable_reconstructs_on_other_account(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    await _enable_api_key_auth(async_client)
    created = await async_client.post(
        "/api/api-keys/", json={"name": "claude-chat-owner-change", "assignedSourceIds": pool}
    )
    assert created.status_code == 200, created.text
    headers = {"Authorization": f"Bearer {created.json()['key']}"}
    tool = {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}}}
    captured, _ = install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {"type": "thinking", "thinking": "prior thought", "signature": "account-bound-signature"},
            {
                "type": "tool_use",
                "id": "owner_call",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {},
            },
        ],
    )
    first = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Look up"}],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert first.status_code == 200, first.text
    original_owner = captured[0][0]
    disabled = await async_client.patch(f"/api/claude-accounts/{original_owner}", json={"isEnabled": False})
    assert disabled.status_code == 200, disabled.text
    captured, _ = install_upstream(monkeypatch)
    followup = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Look up"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "owner_call", "type": "function", "function": {"name": "lookup", "arguments": "{}"}}
                    ],
                    "reasoning_content": "prior thought",
                },
                {"role": "tool", "tool_call_id": "owner_call", "content": "found"},
            ],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert followup.status_code == 200, followup.text
    assert captured[0][0] != original_owner
    sent = json.dumps(captured[0][2])
    assert "account-bound-signature" not in sent
    assert "prior thought" in sent and "owner_call" in sent and "found" in sent


async def test_claude_chat_ambiguous_signed_replay_reconstructs_visible_cycle(async_client, pool, monkeypatch):
    from app.core.config.settings import get_settings
    from app.modules.claude.protocol import ToolIdentity
    from app.modules.proxy._service.websocket.replay_store import HTTPFallbackReplayStore, ReplayScope

    await _enable_api_key_auth(async_client)
    key, key_id = await _create_limited_key(async_client, pool[0], name="claude-chat-ambiguous-replay")
    headers = {"Authorization": f"Bearer {key}"}
    tool = {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}}}
    install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {"type": "thinking", "thinking": "ambiguous thought", "signature": "ambiguous-signature"},
            {
                "type": "tool_use",
                "id": "ambiguous_call",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {},
            },
        ],
    )
    first = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Look up"}],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert first.status_code == 200, first.text
    store = HTTPFallbackReplayStore(get_settings().data_dir / "http-fallback-replay")
    scope = ReplayScope(key_id, "source-responses")
    records = await store.histories(scope)
    assert len(records) == 1
    history = records[0].history
    await store.remember(
        scope,
        "duplicate-response",
        json.dumps({"model": history.model, "input": history.input}),
        history.output,
        history.account_id,
        chat_input=history.chat_input,
        chat_instructions=history.chat_instructions,
    )
    captured, _ = install_upstream(monkeypatch)
    second = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Look up"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "ambiguous_call", "type": "function", "function": {"name": "lookup", "arguments": "{}"}}
                    ],
                    "reasoning_content": "ambiguous thought",
                },
                {"role": "tool", "tool_call_id": "ambiguous_call", "content": "found"},
            ],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert second.status_code == 200, second.text
    sent = json.dumps(captured[0][2])
    assert "ambiguous-signature" not in sent
    assert "ambiguous thought" in sent and "ambiguous_call" in sent and "found" in sent


async def test_claude_chat_model_switch_reconstructs_without_old_signature(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    await _enable_api_key_auth(async_client)
    key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-model-switch")
    headers = {"Authorization": f"Bearer {key}"}
    tool = {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}}}
    install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {"type": "thinking", "thinking": "old model thought", "signature": "old-model-signature"},
            {
                "type": "tool_use",
                "id": "model_call",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {},
            },
        ],
    )
    first = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Look up"}],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert first.status_code == 200, first.text
    captured, _ = install_upstream(monkeypatch)
    second = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "anthropic/claude-sonnet-5",
            "messages": [
                {"role": "user", "content": "Look up"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "model_call", "type": "function", "function": {"name": "lookup", "arguments": "{}"}}
                    ],
                    "reasoning_content": "old model thought",
                },
                {"role": "tool", "tool_call_id": "model_call", "content": "found"},
            ],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert second.status_code == 200, second.text
    sent = json.dumps(captured[0][2])
    assert captured[0][2]["model"] == "claude-sonnet-5"
    assert "old-model-signature" not in sent
    assert "old model thought" in sent and "model_call" in sent and "found" in sent


async def test_claude_chat_reconstructs_image_tool_result_without_losing_media(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Inspect image"},
                {
                    "role": "assistant",
                    "content": "I will inspect it",
                    "tool_calls": [
                        {"id": "image_call", "type": "function", "function": {"name": "inspect", "arguments": "{}"}}
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "image_call",
                    "content": [
                        {"type": "text", "text": "A tiny image"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AQ=="}},
                    ],
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    sent = captured[0][2]["messages"]
    assert any(
        block.get("type") == "image" and block.get("source", {}).get("data") == "AQ=="
        for message in sent
        for block in message["content"]
    )
    assert "A tiny image" in json.dumps(sent)
    assert not any(block.get("type") == "tool_result" for message in sent for block in message["content"])


async def test_claude_chat_stream_retains_signed_tool_turn_before_followup(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    await _enable_api_key_auth(async_client)
    key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-stream-replay")
    headers = {"Authorization": f"Bearer {key}"}
    tool = {"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {}}}}
    install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {"type": "thinking", "thinking": "stream thought", "signature": "stream-signed"},
            {
                "type": "tool_use",
                "id": "stream_replay_call",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {},
            },
        ],
    )
    first = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Find it"}],
            "tools": [tool],
            "reasoning_effort": "high",
            "stream": True,
        },
    )
    assert first.status_code == 200, first.text
    assert first.text.rstrip().endswith("data: [DONE]")
    assert '"id":"stream_replay_call"' in first.text
    captured, _ = install_upstream(monkeypatch)
    followup = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Find it"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "stream_replay_call",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": "{}"},
                        }
                    ],
                    "reasoning_content": "stream thought",
                },
                {"role": "tool", "tool_call_id": "stream_replay_call", "content": "Found"},
            ],
            "tools": [tool],
            "reasoning_effort": "high",
        },
    )
    assert followup.status_code == 200, followup.text
    assert "stream-signed" in json.dumps(captured[0][2])


async def test_claude_chat_truncated_tool_stream_does_not_seed_signed_replay(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    await _enable_api_key_auth(async_client)
    key, _ = await _create_limited_key(async_client, pool[0], name="claude-chat-truncated-replay")
    headers = {"Authorization": f"Bearer {key}"}
    install_upstream(
        monkeypatch,
        truncate=True,
        content=[
            {"type": "thinking", "thinking": "unfinished", "signature": "unfinished-signature"},
            {
                "type": "tool_use",
                "id": "unfinished_call",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {},
            },
        ],
    )
    first = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"model": MODEL, "messages": [{"role": "user", "content": "Look up"}], "stream": True},
    )
    assert '"error"' in first.text
    captured, _ = install_upstream(monkeypatch)
    second = await async_client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": "Look up"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "unfinished_call", "type": "function", "function": {"name": "lookup", "arguments": "{}"}}
                    ],
                    "reasoning_content": "unfinished",
                },
                {"role": "tool", "tool_call_id": "unfinished_call", "content": "result"},
            ],
            "reasoning_effort": "high",
        },
    )
    assert second.status_code == 200, second.text
    assert "unfinished-signature" not in json.dumps(captured[0][2])


async def test_claude_chat_rejects_limit_above_model_ceiling(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_completion_tokens": 200_000,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["param"] == "max_output_tokens"
    assert not captured


async def test_disabled_claude_chat_pool_fails_before_subscription(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    for source_id in pool:
        response = await async_client.patch(f"/api/claude-accounts/{source_id}", json={"isEnabled": False})
        assert response.status_code == 200
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_source_disabled"
    assert not captured


async def test_scoped_key_does_not_fall_through_to_subscription(async_client, pool, monkeypatch):
    await _enable_api_key_auth(async_client)
    other_source = await _create_model_source(
        async_client,
        name="unrelated-chat-source",
        model="unrelated-model",
        base_url="http://127.0.0.1:9/v1",
    )
    created = await async_client.post(
        "/api/api-keys/",
        json={"name": "unrelated-source-key", "assignedSourceIds": [other_source]},
    )
    assert created.status_code == 200
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {created.json()['key']}"},
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "model_source_not_allowed"
    assert not captured


async def test_claude_chat_sampling_controls_reach_messages(async_client, pool, monkeypatch):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions/",
        follow_redirects=True,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.2,
            "top_p": 0.9,
        },
    )
    assert response.status_code == 200, response.text
    assert captured[0][2]["temperature"] == 0.2
    assert captured[0][2]["top_p"] == 0.9


@pytest.mark.parametrize("stream", [False, True])
async def test_claude_chat_early_ended_upstream_is_error(async_client, pool, monkeypatch, stream):
    _, closed = install_upstream(monkeypatch, truncate=True)
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], "stream": stream},
    )
    assert closed
    if stream:
        assert '"error"' in response.text
        assert '"finish_reason":"stop"' not in response.text
    else:
        assert response.status_code == 502
        assert "error" in response.json()


@pytest.mark.parametrize("stream", [False, True])
async def test_claude_chat_refusal_maps_content_filter(async_client, pool, monkeypatch, stream):
    install_upstream(monkeypatch, stop="refusal")
    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], "stream": stream},
    )
    assert response.status_code == 200, response.text
    if stream:
        assert '"finish_reason":"content_filter"' in response.text
    else:
        assert response.json()["choices"][0]["finish_reason"] == "content_filter"


async def test_claude_chat_stream_exposes_reasoning_delta_without_signature(async_client, pool, monkeypatch):
    from app.modules.claude import transport

    async def open_stream(source, path, payload, **kwargs):
        del source, path, payload, kwargs
        events = [
            {"type": "message_start", "message": {"id": "msg_thinking", "usage": {"input_tokens": 2}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": ""}},
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": "Check premise"},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "signature_delta", "signature": "private-signature"},
            },
            {"type": "content_block_stop", "index": 0},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Answer"}},
            {"type": "content_block_stop", "index": 1},
            {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 3}},
            {"type": "message_stop"},
        ]

        async def chunks(_size):
            for event in events:
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode()

        response = SimpleNamespace(status=200, headers={}, content=SimpleNamespace(iter_chunked=chunks))
        return AsyncExitStack(), response, None

    monkeypatch.setattr(transport, "_open_source_stream", open_stream)
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "reasoning_effort": "medium",
            "stream": True,
        },
    )
    assert response.status_code == 200, response.text
    assert '"reasoning_content":"Check premise"' in response.text
    assert '"content":"Answer"' in response.text
    assert "private-signature" not in response.text


async def test_claude_chat_stream_emits_function_call_and_usage(async_client, pool, monkeypatch):
    from app.modules.claude.protocol import ToolIdentity

    install_upstream(
        monkeypatch,
        stop="tool_use",
        content=[
            {
                "type": "tool_use",
                "id": "tool_stream_1",
                "name": ToolIdentity("lookup", None, False).wire_name,
                "input": {"city": "Berlin"},
            }
        ],
    )
    response = await async_client.post(
        "/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Weather?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup",
                        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
                    },
                }
            ],
            "stream": True,
            "stream_options": {"include_usage": True},
        },
    )
    assert response.status_code == 200, response.text
    chunks = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: {")]
    calls = [
        call
        for chunk in chunks
        for choice in chunk.get("choices", [])
        for call in choice["delta"].get("tool_calls", [])
    ]
    assert any(call.get("id") == "tool_stream_1" for call in calls)
    assert any(call.get("function", {}).get("name") == "lookup" for call in calls)
    assert any(call.get("function", {}).get("arguments") == '{"city":"Berlin"}' for call in calls)
    assert any(choice.get("finish_reason") == "tool_calls" for chunk in chunks for choice in chunk.get("choices", []))
    assert any(chunk.get("usage", {}).get("total_tokens") == 17 for chunk in chunks if chunk.get("usage"))


@pytest.mark.parametrize("stream", [False, True])
async def test_claude_chat_has_one_finalized_api_key_reservation(async_client, pool, monkeypatch, stream):
    await _enable_api_key_auth(async_client)
    key, key_id = await _create_limited_key(async_client, pool[0], name=f"claude-chat-{stream}")
    captured, closed = install_upstream(monkeypatch)
    response = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], "stream": stream},
    )
    assert response.status_code == 200, response.text
    assert len(captured) == 1
    assert closed == [pool[0]]
    reservations = await _reservations(key_id)
    assert [reservation.status for reservation in reservations] == ["finalized"]
    assert reservations[0].input_tokens == 10
    assert reservations[0].output_tokens == 7


async def test_claude_chat_stream_error_releases_single_reservation(async_client, pool, monkeypatch):
    await _enable_api_key_auth(async_client)
    key, key_id = await _create_limited_key(async_client, pool[0], name="claude-chat-stream-error")
    _, closed = install_upstream(monkeypatch, truncate=True)
    response = await async_client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": MODEL, "messages": [{"role": "user", "content": "Hello"}], "stream": True},
    )
    assert response.status_code == 200
    assert '"error"' in response.text
    assert closed == [pool[0]]
    reservations = await _reservations(key_id)
    assert [reservation.status for reservation in reservations] == ["released"]
