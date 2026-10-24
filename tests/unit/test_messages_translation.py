from __future__ import annotations

import base64
import json

import pytest

from app.core.messages.alias import decode_discovery_alias, discovery_alias
from app.core.messages.envelope import ReasoningEnvelope, seal_reasoning, strip_proxy_thinking
from app.core.messages.errors import MessagesRequestError, anthropic_error
from app.core.messages.stream import MessagesStreamProjector, aggregate_message
from app.core.messages.tokens import estimate_input_tokens
from app.core.messages.translate import (
    MessagesIdentity,
    messages_identity,
    tool_alias,
    translate_messages_request,
)

KEY = b"k" * 32
MODEL = "gpt-6.1-sol"
SESSION = MessagesIdentity(session_id="11111111-1111-4111-8111-111111111111", agent_id="main")
LONG_NAME = "mcp__" + "very_long_server_name_" * 3 + "__lookup"


def _translate(body: dict, *, identity: MessagesIdentity = SESSION, model: str = MODEL):
    return translate_messages_request({"model": model, **body}, model=model, identity=identity, envelope_key=KEY)


def _signature(model: str = MODEL, item_id: str = "rs_1", encrypted: str = "enc-1") -> str:
    return seal_reasoning(ReasoningEnvelope(model=model, item_id=item_id, encrypted_content=encrypted), KEY)


def _forged_signature() -> str:
    encoded = _signature()[5:]
    body = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    body["id"] = "rs_2"
    return "clb1:" + base64.urlsafe_b64encode(json.dumps(body).encode()).decode()


def test_system_tools_and_history_translation():
    translated = _translate(
        {
            "system": [
                {"type": "text", "text": "x-anthropic-billing-header: cc_version=2.1"},
                {"type": "text", "text": "You are Claude Code.", "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "Project rules."},
            ],
            "tools": [
                {
                    "name": LONG_NAME,
                    "description": "Lookup",
                    "input_schema": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "properties": {"q": {"type": "string", "pattern": "^\\p{L}+$"}},
                    },
                    "cache_control": {"type": "ephemeral"},
                    "defer_loading": True,
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Read this"},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}},
                        {
                            "type": "document",
                            "title": "spec.pdf",
                            "source": {"type": "base64", "media_type": "application/pdf", "data": "JVBE"},
                        },
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "plan", "signature": _signature()},
                        {"type": "text", "text": "Looking."},
                        {"type": "tool_use", "id": "toolu_" + "x" * 70, "name": LONG_NAME, "input": {"q": "a"}},
                    ],
                },
                {"role": "system", "content": "Reminder"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_" + "x" * 70,
                            "content": [
                                {"type": "text", "text": "found"},
                                {"type": "image", "source": {"type": "url", "url": "https://example.test/a.png"}},
                            ],
                        },
                        {"type": "text", "text": "Continue"},
                    ],
                },
            ],
            "max_tokens": 4096,
            "temperature": 1,
            "metadata": {"user_id": "opaque"},
            "context_management": {"edits": []},
        }
    )
    payload = translated.payload
    assert payload["instructions"] == "You are Claude Code.\n\nProject rules."
    assert payload["store"] is False and payload["stream"] is True
    assert payload["include"] == ["reasoning.encrypted_content"]
    assert payload["max_output_tokens"] == 4096 and payload["temperature"] == 1
    assert "metadata" not in payload and "context_management" not in payload
    alias = tool_alias(LONG_NAME)
    assert len(alias) == 64 and translated.tool_names == {alias: LONG_NAME}
    assert payload["tools"] == [
        {
            "type": "function",
            "name": alias,
            "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
            "strict": False,
            "description": "Lookup",
        }
    ]
    assert payload["tool_choice"] == "auto" and payload["parallel_tool_calls"] is True
    call_id = tool_alias("toolu_" + "x" * 70)
    assert payload["input"] == [
        {
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Read this"},
                {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
                {"type": "input_file", "filename": "spec.pdf", "file_data": "data:application/pdf;base64,JVBE"},
            ],
        },
        {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "enc-1"},
        {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Looking."}]},
        {"type": "function_call", "call_id": call_id, "name": alias, "arguments": '{"q":"a"}'},
        {
            "type": "function_call_output",
            "call_id": call_id,
            "output": [
                {"type": "input_text", "text": "found"},
                {"type": "input_image", "image_url": "https://example.test/a.png"},
            ],
        },
        {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "Reminder"}]},
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Continue"}]},
    ]


def test_foreign_and_other_model_thinking_and_search_replay_are_omitted():
    translated = _translate(
        {
            "messages": [
                {"role": "user", "content": "Hi"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "a", "signature": _signature(model="gpt-6-astra")},
                        {"type": "thinking", "thinking": "b", "signature": "EqQBClaudeSignature"},
                        {"type": "thinking", "thinking": "c", "signature": ""},
                        {"type": "redacted_thinking", "data": "opaque"},
                        {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_search", "input": {"query": "q"}},
                        {"type": "web_search_tool_result", "tool_use_id": "srvtoolu_1", "content": []},
                        {"type": "text", "text": "Answer"},
                    ],
                },
            ]
        }
    )
    assert translated.payload["input"] == [
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Hi"}]},
        {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Answer"}]},
    ]


@pytest.mark.parametrize(
    "signature",
    ["clb1:not-base64!", "clb1:" + _signature()[5:-4] + "AAAA", _forged_signature()],
)
def test_forged_or_malformed_envelope_is_rejected(signature):
    with pytest.raises(MessagesRequestError):
        _translate(
            {
                "messages": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": [{"type": "thinking", "thinking": "", "signature": signature}]},
                ]
            }
        )


def test_native_path_strips_proxy_thinking_and_empty_assistant_messages():
    body = {
        "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": [{"type": "thinking", "thinking": "a", "signature": _signature()}]},
            {"role": "user", "content": "Again"},
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "b", "signature": _signature()},
                    {"type": "thinking", "thinking": "c", "signature": "EqQBClaude"},
                    {"type": "text", "text": "Done"},
                ],
            },
        ]
    }
    strip_proxy_thinking(body)
    assert body["messages"] == [
        {"role": "user", "content": "Hi"},
        {"role": "user", "content": "Again"},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "c", "signature": "EqQBClaude"},
                {"type": "text", "text": "Done"},
            ],
        },
    ]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"stop_sequences": ["END"]}, "stop_sequences"),
        ({"top_k": 5}, "top_k"),
        ({"mcp_servers": [{"type": "url", "url": "https://mcp.test"}]}, "mcp_servers"),
        ({"tools": [{"type": "code_execution_20250825", "name": "code_execution"}]}, "code_execution_20250825"),
    ],
)
def test_fields_without_responses_equivalent_are_rejected(body, message):
    with pytest.raises(MessagesRequestError, match=message):
        _translate({"messages": [{"role": "user", "content": "Hi"}], **body})


def test_tool_choice_web_search_and_controls():
    translated = _translate(
        {
            "messages": [{"role": "user", "content": "Hi"}],
            "tools": [
                {"type": "web_search_20250305", "name": "web_search", "allowed_domains": ["example.test"]},
                {"name": "Read", "input_schema": {"type": "object"}},
            ],
            "tool_choice": {"type": "tool", "name": "web_search", "disable_parallel_tool_use": True},
            "output_config": {
                "effort": "HIGH",
                "format": {"type": "json_schema", "schema": {"type": "object", "properties": {"a": {}}}},
            },
            "speed": "fast",
        }
    )
    payload = translated.payload
    assert payload["tools"][0] == {"type": "web_search", "filters": {"allowed_domains": ["example.test"]}}
    assert payload["tools"][1]["parameters"] == {"type": "object", "properties": {}}
    assert payload["include"] == ["reasoning.encrypted_content", "web_search_call.action.sources"]
    assert payload["tool_choice"] == {"type": "web_search"}
    assert payload["parallel_tool_calls"] is False
    assert payload["reasoning"] == {"effort": "high", "summary": "auto"}
    assert payload["text"]["format"]["strict"] is False
    assert payload["service_tier"] == "priority"
    for choice, expected in (
        ({"type": "any"}, "required"),
        ({"type": "none"}, "none"),
        ({"type": "tool", "name": "Read"}, {"type": "function", "name": "Read"}),
    ):
        body = {"messages": [{"role": "user", "content": "Hi"}], "tools": [{"name": "Read"}], "tool_choice": choice}
        assert _translate(body).payload["tool_choice"] == expected


@pytest.mark.parametrize(
    ("thinking", "expected"),
    [
        ({"type": "enabled", "budget_tokens": 512}, {"effort": "minimal", "summary": "auto"}),
        ({"type": "enabled", "budget_tokens": 1024}, {"effort": "low", "summary": "auto"}),
        ({"type": "enabled", "budget_tokens": 8000}, {"effort": "medium", "summary": "auto"}),
        ({"type": "enabled", "budget_tokens": 24576}, {"effort": "high", "summary": "auto"}),
        ({"type": "enabled", "budget_tokens": 32000}, {"effort": "xhigh", "summary": "auto"}),
        ({"type": "disabled"}, {"effort": "none"}),
        ({"type": "adaptive"}, {"summary": "auto"}),
        ({"type": "adaptive", "display": "omitted"}, None),
    ],
)
def test_thinking_maps_to_reasoning(thinking, expected):
    payload = _translate({"messages": [{"role": "user", "content": "Hi"}], "thinking": thinking}).payload
    assert payload.get("reasoning") == expected


def test_identity_scopes_prompt_cache_key():
    session = "22222222-2222-4222-8222-222222222222"
    headers = {"X-Claude-Code-Session-Id": session}
    body = {"messages": [{"role": "user", "content": "Hi"}]}
    main = messages_identity(body, headers)
    agent = messages_identity(body, {**headers, "x-claude-code-agent-id": "agent-7"})
    assert main == MessagesIdentity(session_id=session, agent_id="main")
    assert (
        _translate(body, identity=main).payload["prompt_cache_key"]
        != _translate(body, identity=agent).payload["prompt_cache_key"]
    )
    metadata = {"user_id": json.dumps({"device_id": "d", "session_id": session})}
    assert messages_identity({"metadata": metadata}, {}) == main
    assert messages_identity({"metadata": {"user_id": "opaque"}}, {}).session_id is None
    with pytest.raises(MessagesRequestError):
        messages_identity({"metadata": metadata}, {"x-claude-code-session-id": "other"})
    anonymous = MessagesIdentity(session_id=None, agent_id="main")
    first = _translate(body, identity=anonymous).payload["prompt_cache_key"]
    assert (
        first
        == _translate({"messages": [{"role": "user", "content": "Other"}]}, identity=anonymous).payload[
            "prompt_cache_key"
        ]
    )
    assert first != _translate({**body, "system": "Different"}, identity=anonymous).payload["prompt_cache_key"]


def _feed(projector: MessagesStreamProjector, events: list[dict]) -> list[dict]:
    out: list[dict] = []
    for event in events:
        out.extend(projector.feed(event))
    return out


def test_tool_turn_projection():
    alias = tool_alias(LONG_NAME)
    projector = MessagesStreamProjector(
        model=MODEL, reported_model=MODEL, tool_names={alias: LONG_NAME}, envelope_key=KEY
    )
    out = _feed(
        projector,
        [
            {"type": "response.created", "response": {"id": "resp_abc"}},
            {"type": "response.output_item.added", "item": {"id": "rs_1", "type": "reasoning"}},
            {"type": "response.reasoning_summary_text.delta", "item_id": "rs_1", "summary_index": 0, "delta": "Plan"},
            {"type": "response.reasoning_summary_text.delta", "item_id": "rs_1", "summary_index": 1, "delta": "More"},
            {
                "type": "response.output_item.done",
                "item": {"id": "rs_1", "type": "reasoning", "encrypted_content": "enc-1", "summary": []},
            },
            {"type": "response.output_item.added", "item": {"id": "msg_c", "type": "message", "phase": "commentary"}},
            {"type": "response.output_text.delta", "item_id": "msg_c", "delta": "Checking"},
            {"type": "response.output_item.done", "item": {"id": "msg_c", "type": "message", "content": []}},
            {
                "type": "response.output_item.added",
                "item": {"id": "fc_1", "type": "function_call", "call_id": "call_1"},
            },
            {"type": "response.function_call_arguments.delta", "item_id": "fc_1", "delta": '{"q":'},
            {
                "type": "response.output_item.done",
                "item": {
                    "id": "fc_1",
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": alias,
                    "arguments": '{"q":"a"}',
                },
            },
            {
                "type": "response.completed",
                "response": {
                    "id": "resp_abc",
                    "usage": {
                        "input_tokens": 10000,
                        "output_tokens": 50,
                        "input_tokens_details": {"cached_tokens": 8000, "cache_write_tokens": 500},
                    },
                },
            },
        ],
    )
    assert projector.message_start()["message"]["id"] == "msg_abc"
    assert [event["type"] for event in out] == [
        "content_block_start",
        "content_block_delta",
        "content_block_delta",
        "content_block_delta",
        "content_block_stop",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    assert out[2]["delta"] == {"type": "thinking_delta", "thinking": "\n\nMore"}
    assert out[3]["delta"]["signature"] == _signature()
    assert out[5]["content_block"]["type"] == "thinking" and out[6]["delta"]["thinking"] == "Checking"
    assert out[8]["content_block"] == {"type": "tool_use", "id": "call_1", "name": LONG_NAME, "input": {}}
    assert out[9]["delta"] == {"type": "input_json_delta", "partial_json": '{"q":"a"}'}
    assert out[11]["delta"]["stop_reason"] == "tool_use"
    assert out[11]["usage"] == {
        "input_tokens": 1500,
        "cache_read_input_tokens": 8000,
        "cache_creation_input_tokens": 500,
        "output_tokens": 50,
    }
    message = aggregate_message(projector.message_start(), out)
    assert [block["type"] for block in message["content"]] == ["thinking", "thinking", "tool_use"]
    assert message["content"][0] == {"type": "thinking", "thinking": "Plan\n\nMore", "signature": _signature()}
    assert message["content"][2]["input"] == {"q": "a"}
    assert message["stop_reason"] == "tool_use"


def test_text_web_search_and_incomplete_projection():
    projector = MessagesStreamProjector(model=MODEL, reported_model=MODEL, tool_names={}, envelope_key=KEY)
    out = _feed(
        projector,
        [
            {
                "type": "response.output_item.done",
                "item": {
                    "id": "ws_1",
                    "type": "web_search_call",
                    "action": {
                        "type": "search",
                        "query": "news",
                        "sources": [{"type": "url", "url": "https://a.test"}],
                    },
                },
            },
            {
                "type": "response.output_item.done",
                "item": {
                    "id": "msg_1",
                    "type": "message",
                    "phase": "final_answer",
                    "content": [{"type": "output_text", "text": "Answer"}],
                },
            },
            {"type": "response.incomplete", "response": {"incomplete_details": {"reason": "max_output_tokens"}}},
        ],
    )
    message = aggregate_message(projector.message_start(), out)
    assert message["content"] == [
        {"type": "server_tool_use", "id": "ws_1", "name": "web_search", "input": {"query": "news"}},
        {
            "type": "web_search_tool_result",
            "tool_use_id": "ws_1",
            "content": [
                {"type": "web_search_result", "title": "https://a.test", "url": "https://a.test", "page_age": None}
            ],
        },
        {"type": "text", "text": "Answer"},
    ]
    assert message["stop_reason"] == "max_tokens"


def test_failures_before_and_after_output():
    overflow = {"code": "context_length_exceeded", "message": "Input exceeds the context window"}
    projector = MessagesStreamProjector(model=MODEL, reported_model=MODEL, tool_names={}, envelope_key=KEY)
    assert _feed(projector, [{"type": "response.failed", "response": {"error": overflow}}]) == []
    assert projector.failure == (
        400,
        {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "prompt is too long: Input exceeds the context window",
            },
        },
    )
    projector = MessagesStreamProjector(model=MODEL, reported_model=MODEL, tool_names={}, envelope_key=KEY)
    out = _feed(projector, [{"type": "response.output_text.delta", "item_id": "m", "delta": "Hi"}])
    out += projector.end_of_stream()
    assert projector.failure is None
    assert [event["type"] for event in out] == [
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "error",
    ]


@pytest.mark.parametrize(
    ("status", "error", "expected"),
    [
        (429, {"code": "usage_limit_reached", "message": "limit"}, (429, "rate_limit_error")),
        (502, {"code": "server_is_overloaded", "message": "busy"}, (529, "overloaded_error")),
        (401, {"message": "bad"}, (401, "authentication_error")),
        (403, {"type": "permission_error", "message": "no"}, (403, "permission_error")),
        (400, {"code": "invalid_value", "message": "bad"}, (400, "invalid_request_error")),
        (503, {"code": "no_accounts", "message": "none"}, (503, "api_error")),
    ],
)
def test_error_mapping(status, error, expected):
    mapped_status, envelope = anthropic_error(status, error)
    assert (mapped_status, envelope["error"]["type"]) == expected


def test_token_estimate_bounds_attachments():
    image = "data:image/png;base64," + "A" * 2_000_000
    payload = {"instructions": "x" * 400, "input": [{"type": "input_image", "image_url": image}], "tools": []}
    assert estimate_input_tokens(payload) < 5_000


@pytest.mark.parametrize(
    ("model", "alias"),
    [
        ("gpt-6.1-sol", "clb-claude-gpt-6.1-sol"),
        ("openrouter/z-ai/glm-5.3-flash", "clb-claude-openrouter~sz-ai~sglm-5.3-flash"),
        ("lab/a~s", "clb-claude-lab~sa~ts"),
    ],
)
def test_discovery_alias_round_trip(model, alias):
    assert discovery_alias(model) == alias
    assert decode_discovery_alias(alias) == model
    assert "claude" in alias and not alias.startswith("claude-")


def test_discovery_alias_leaves_model_names_and_rejects_invalid_aliases():
    assert decode_discovery_alias("claude-opus-5-5") == "claude-opus-5-5"
    assert decode_discovery_alias("gpt-6.1-sol") == "gpt-6.1-sol"
    for invalid in ("clb-claude-", "clb-claude-gpt~x", "clb-claude-gpt~"):
        with pytest.raises(MessagesRequestError):
            decode_discovery_alias(invalid)


def test_projection_reports_requested_model_and_seals_routed_model():
    alias = discovery_alias(MODEL)
    projector = MessagesStreamProjector(model=MODEL, reported_model=alias, tool_names={}, envelope_key=KEY)
    out = _feed(
        projector,
        [
            {
                "type": "response.output_item.done",
                "item": {"id": "rs_1", "type": "reasoning", "summary": [], "encrypted_content": "enc-1"},
            },
            {"type": "response.completed", "response": {"usage": {"input_tokens": 1, "output_tokens": 1}}},
        ],
    )
    message = aggregate_message(projector.message_start(), out)
    assert message["model"] == alias
    assert message["content"][0]["signature"] == _signature()
