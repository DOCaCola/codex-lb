import json
from copy import deepcopy
from typing import Any

import pytest

from app.core.clients.proxy import _restore_native_collaboration_block
from app.core.clients.proxy_websocket import UpstreamWebSocketMessage
from app.core.clients.responses_transport import _restore_native_collaboration_message
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.requests import ResponsesRequest, sanitize_native_responses_input
from app.core.openai.subagent_messages import (
    lower_agent_messages,
    project_native_collaboration_tools,
    restore_native_collaboration,
)
from app.core.utils.sse import ParsedSseBlock, format_sse_event, parse_sse_data_json
from app.db.models import ModelSource, ModelSourceModel
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.protocol import project_responses

pytestmark = pytest.mark.unit

# JSON fixtures are typed ``Any`` so assertions can index nested values.
ENCRYPTED: Any = {"type": "string", "encrypted": True, "description": "Message"}
SEND: Any = {
    "type": "function",
    "name": "send_message",
    "parameters": {"type": "object", "properties": {"target": {"type": "string"}, "message": ENCRYPTED}},
}
COLLABORATION: Any = {"type": "namespace", "name": "collaboration", "description": "Agents", "tools": [SEND]}
SHELL: Any = {"type": "function", "name": "shell", "parameters": {"type": "object", "properties": {"m": ENCRYPTED}}}
UPSTREAM_CALL: Any = {
    "type": "function_call",
    "namespace": "collaboration-optimize",
    "name": "send_message",
    "call_id": "call_1",
    "arguments": '{"target":"/root","message":"done"}',
}
HEADER: Any = {"type": "input_text", "text": "Task name: /root\nSender: /root/worker\nPayload:\n"}


def agent_message(*parts: Any) -> Any:
    return {"type": "agent_message", "author": "/root/worker", "recipient": "/root", "content": list(parts)}


def test_native_projection_renames_collaboration_and_drops_encryption_markers():
    payload: Any = {
        "tools": [COLLABORATION, SHELL],
        "input": [
            {"type": "additional_tools", "tools": [COLLABORATION]},
            {**UPSTREAM_CALL, "namespace": "collaboration"},
        ],
    }
    original = deepcopy(payload)
    projected: Any = project_native_collaboration_tools(payload)

    assert payload == original
    namespace = projected["tools"][0]
    assert namespace["name"] == "collaboration-optimize" and namespace["description"] == "Agents"
    assert namespace["tools"][0]["parameters"]["properties"]["message"] == {"type": "string", "description": "Message"}
    assert projected["tools"][1] == SHELL
    assert projected["input"][0]["tools"] == [namespace]
    assert projected["input"][1] == original["input"][1]
    sanitized: Any = sanitize_native_responses_input(payload)
    assert sanitized["tools"][0] == namespace


def test_native_projection_leaves_payloads_without_collaboration_untouched():
    payload: Any = {"tools": [SHELL], "input": [{"role": "user", "content": "hi"}]}
    assert project_native_collaboration_tools(payload) == payload


def test_restoration_marks_plaintext_calls_and_renames_echoed_declarations():
    event: Any = {
        "type": "response.completed",
        "response": {"output": [UPSTREAM_CALL], "tools": [{**COLLABORATION, "name": "collaboration-optimize"}]},
    }
    original = deepcopy(event)
    restored: Any = restore_native_collaboration(event)

    assert event == original
    assert restored["response"]["output"][0] == {
        **UPSTREAM_CALL,
        "namespace": "collaboration",
        "encrypted_function_args": [],
    }
    assert restored["response"]["tools"][0]["name"] == "collaboration"
    assert restore_native_collaboration({"type": "response.output_text.delta", "delta": "x"}) is None


def test_stream_block_restoration_keeps_block_metadata():
    payload: Any = {"type": "response.output_item.done", "item": UPSTREAM_CALL}
    block = ParsedSseBlock(format_sse_event(payload), payload, is_local=False, response_id_is_local=True)

    restored = _restore_native_collaboration_block(block)

    restored_payload: Any = parse_sse_data_json(restored)
    assert restored_payload["item"]["namespace"] == "collaboration"
    assert isinstance(restored, ParsedSseBlock) and restored.response_id_is_local
    assert payload["item"]["namespace"] == "collaboration-optimize"
    plain = format_sse_event({"type": "response.output_text.delta", "delta": "hi"})
    assert _restore_native_collaboration_block(plain) is plain


@pytest.mark.parametrize("parsed", [True, False])
def test_websocket_restoration_rewrites_text_and_payload(parsed):
    payload: Any = {"type": "response.output_item.added", "item": UPSTREAM_CALL}
    message = UpstreamWebSocketMessage(kind="text", text=json.dumps(payload), payload=payload if parsed else None)

    restored = _restore_native_collaboration_message(message)

    assert restored.text is not None
    assert json.loads(restored.text)["item"]["encrypted_function_args"] == []
    assert (restored.payload is not None) is parsed
    if parsed:
        assert restored.payload == json.loads(restored.text)
    assert payload["item"] == UPSTREAM_CALL


def test_plaintext_agent_message_becomes_user_message_with_codex_header():
    payload: Any = {"input": [{"role": "user", "content": "go"}, agent_message({"type": "input_text", "text": "done"})]}
    lowered: Any = lower_agent_messages(payload)

    assert lowered["input"][1] == {
        "type": "message",
        "role": "user",
        "content": [HEADER, {"type": "input_text", "text": "done"}],
    }
    assert payload["input"][1]["type"] == "agent_message"


def test_encrypted_agent_message_fails_explicitly():
    message = agent_message(
        {"type": "input_text", "text": "Payload:\n"}, {"type": "encrypted_content", "encrypted_content": "gAAAA"}
    )
    with pytest.raises(ClientPayloadError) as error:
        lower_agent_messages({"input": [message]})
    assert error.value.code == "nonportable_agent_message"
    assert error.value.param == "input[0]"


def test_claude_parent_receives_child_report_after_tool_cycle():
    payload: Any = lower_agent_messages(
        {
            "model": "anthropic/claude-haiku-4-5",
            "input": [
                {"role": "user", "content": "delegate"},
                {"type": "function_call", "name": "wait", "call_id": "call", "arguments": "{}"},
                {"type": "function_call_output", "call_id": "call", "output": "woken"},
                agent_message({"type": "input_text", "text": "progress"}),
            ],
            "tools": [{"type": "function", "name": "wait", "parameters": {"type": "object"}}],
        }
    )
    body: Any = project_responses(
        payload, max_output_tokens=64000, reasoning=reasoning_spec(payload["model"], None)
    ).body

    final = body["messages"][-1]
    texts = [block["text"] for block in final["content"] if block.get("type") == "text"]
    assert final["role"] == "user"
    assert texts[-2:] == [HEADER["text"], "progress"]


def test_model_source_receives_lowered_agent_message():
    from app.modules.proxy.api import _shape_source_responses_payload

    request = ResponsesRequest.model_validate(
        {
            "model": "source",
            "instructions": "",
            "input": [{"role": "user", "content": "go"}, agent_message({"type": "input_text", "text": "done"})],
        }
    )
    source = ModelSource(
        id="source",
        name="Source",
        kind="openai_compatible",
        supports_responses=True,
        models=[ModelSourceModel(model="source", is_enabled=True)],
    )
    wire: Any = _shape_source_responses_payload(request, source, api_key=None)
    assert wire["input"][1] == {
        "type": "message",
        "role": "user",
        "content": [HEADER, {"type": "input_text", "text": "done"}],
    }
