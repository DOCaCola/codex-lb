import json

import pytest
from cryptography.fernet import Fernet
from pydantic import JsonValue

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import project_responses
from app.modules.claude.responses import ResponsesProjection
from tests.claude_json_helpers import array, at

pytestmark = pytest.mark.unit


def request(**overrides):
    return {"model": "anthropic/claude-opus-5", "input": "Hello", **overrides}


def test_structured_output_and_reasoning_share_output_configuration():
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    result = project_responses(
        request(text={"format": {"type": "json_schema", "schema": schema}}, reasoning={"effort": "high"}),
        max_output_tokens=8192,
    )
    assert result.body["output_config"] == {"effort": "high", "format": {"type": "json_schema", "schema": schema}}


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "anthropic/claude-opus-5-99", "reasoning": {"effort": "high"}},
        {"service_tier": "priority"},
        {"truncation": "auto"},
        {"tools": [{"type": "custom", "name": "grammar", "format": {"type": "grammar", "definition": "x"}}]},
    ],
)
def test_unsupported_semantics_are_not_silently_dropped(payload):
    with pytest.raises(ClientPayloadError):
        project_responses(request(**payload), max_output_tokens=8192)


def scope():
    return OpaqueScope("source-a", "anthropic/claude-opus-5", "key-a", "thread-a")


def codec():
    return ClaudeOpaqueState(TokenEncryptor(key=Fernet.generate_key()))


def test_text_and_inline_image_projection_does_not_mutate_input():
    payload = request(
        instructions="Keep instructions",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Inspect"},
                    {"type": "input_image", "image_url": "data:image/png;base64,aGVsbG8="},
                ],
            }
        ],
    )
    before = json.dumps(payload)
    projected = project_responses(payload, max_output_tokens=8192)
    assert projected.body["system"] == [{"type": "text", "text": "Keep instructions"}]
    assert at(projected.body, "messages", 0, "content", 1, "source", "media_type") == "image/png"
    assert json.dumps(payload) == before


def test_namespace_custom_tool_roundtrip_with_signed_thinking():
    payload = request(
        tools=[
            {
                "type": "namespace",
                "name": "functions",
                "tools": [
                    {"type": "custom", "name": "exec", "description": "Run input"},
                ],
            }
        ]
    )
    projected = project_responses(payload, max_output_tokens=8192)
    wire = next(iter(projected.tools))
    opaque = codec()
    adapter = ResponsesProjection(scope(), projected.tools, opaque)
    response = adapter.complete(
        {
            "id": "msg1",
            "stop_reason": "tool_use",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cache_read_input_tokens": 30,
                "cache_creation_input_tokens": 40,
            },
            "content": [
                {"type": "thinking", "thinking": "preserve", "signature": "signed"},
                {"type": "text", "text": "Run tool"},
                {"type": "tool_use", "id": "call1", "name": wire, "input": {"input": "hello\nworld"}},
            ],
        }
    )
    assert at(response, "usage", "input_tokens") == 80
    assert at(response, "usage", "total_tokens") == 100
    tool = at(response, "output", -1)
    assert isinstance(tool, dict)
    assert (tool["name"], tool["namespace"], tool["input"]) == ("exec", "functions", "hello\nworld")
    history = [
        {"role": "user", "content": "Hello"},
        *array(response["output"]),
        {"type": "custom_tool_call_output", "call_id": "call1", "output": "done"},
    ]
    replay = project_responses(
        request(tools=payload["tools"], input=history),
        max_output_tokens=8192,
        restore_reasoning=lambda token: (
            opaque.decode(
                token, model=scope().model, client_scope=scope().client_scope, conversation_id=scope().conversation_id
            ).block
        ),
    )
    assert at(replay.body, "messages", 1, "content") == [
        {"type": "thinking", "thinking": "preserve", "signature": "signed"},
        {"type": "text", "text": "Run tool"},
        {"type": "tool_use", "id": "call1", "name": wire, "input": {"input": "hello\nworld"}},
    ]
    assert at(replay.body, "messages", 2, "content", 0, "tool_use_id") == "call1"


@pytest.mark.parametrize(
    "field,value", [("model", "anthropic/claude-sonnet-5"), ("client_scope", "key-b"), ("conversation_id", "thread-b")]
)
def test_opaque_state_cannot_cross_scope(field, value):
    opaque = codec()
    token = opaque.encode(scope(), {"type": "redacted_thinking", "data": "opaque"})
    args = {
        "model": scope().model,
        "client_scope": scope().client_scope,
        "conversation_id": scope().conversation_id,
        field: value,
    }
    with pytest.raises(ClientPayloadError):
        opaque.decode(token, **args)


@pytest.mark.parametrize(
    "stop,status",
    [("end_turn", "completed"), ("tool_use", "completed"), ("max_tokens", "incomplete"), ("pause_turn", "incomplete")],
)
def test_terminal_semantics(stop, status):
    response = ResponsesProjection(scope(), {}, codec()).complete(
        {
            "id": "m",
            "content": [{"type": "text", "text": "answer"}],
            "stop_reason": stop,
            "usage": {},
        }
    )
    assert response["status"] == status


def test_stream_lifecycle_and_signature_deltas():
    opaque = codec()
    adapter = ResponsesProjection(scope(), {}, opaque)
    events = []
    native_events: list[dict[str, JsonValue]] = [
        {"type": "message_start", "message": {"id": "m", "usage": {"input_tokens": 12}}},
        {"type": "ping"},
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking", "thinking": "", "signature": ""},
        },
        {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "reason"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "sig"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "hello"}},
        {"type": "content_block_stop", "index": 1},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 8}},
        {"type": "message_stop"},
    ]
    for event in native_events:
        events.extend(adapter.consume(event))
    assert [event["sequence_number"] for event in events] == list(range(len(events)))
    assert events[-1]["type"] == "response.completed"
    assert at(events[-1], "response", "usage", "input_tokens") == 12
    assert at(events[-1], "response", "output", 1, "content", 0, "text") == "hello"
    assert not any("reason" in str(event.get("delta", "")) for event in events)


def test_early_stop_is_not_completed():
    adapter = ResponsesProjection(scope(), {}, codec())
    adapter.consume({"type": "message_start", "message": {"id": "m"}})
    with pytest.raises(ClaudeError):
        adapter.consume({"type": "message_stop"})
    assert not adapter.stopped


@pytest.mark.parametrize(
    "item",
    [
        {"type": "function_call_output", "call_id": "missing", "output": "result"},
        {"type": "item_reference", "id": "missing"},
        {"role": "user", "content": [{"type": "input_image", "image_url": "file:///private"}]},
    ],
)
def test_unsupported_or_orphaned_history_rejected(item):
    with pytest.raises(ClientPayloadError):
        project_responses(request(input=[item]), max_output_tokens=8192)
