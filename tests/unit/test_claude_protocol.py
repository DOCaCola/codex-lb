import json
import logging
from copy import deepcopy

import pytest
from cryptography.fernet import Fernet
from pydantic import JsonValue

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.capabilities import ReasoningSpec, reasoning_spec
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import project_responses
from app.modules.claude.responses import ResponsesProjection
from app.modules.claude.tool_names import ClaudeToolNames
from tests.claude_json_helpers import array, at

pytestmark = pytest.mark.unit


def project(payload, **kwargs):
    """Project with the policy-derived reasoning the payload's model would get."""
    return project_responses(payload, reasoning=reasoning_spec(str(payload.get("model", "")), None), **kwargs)


def request(**overrides):
    return {"model": "anthropic/claude-opus-5", "input": "Hello", **overrides}


@pytest.mark.parametrize("maximum,expected", [(128000, 64000), (64000, 64000), (32000, 32000)])
def test_default_output_budget_is_distinct_from_capability(maximum, expected):
    assert project(request(), max_output_tokens=maximum).body["max_tokens"] == expected


def test_explicit_output_budget_can_exceed_default_but_not_capability():
    assert project(request(max_output_tokens=100000), max_output_tokens=128000).body["max_tokens"] == 100000
    with pytest.raises(ClientPayloadError):
        project(request(max_output_tokens=128001), max_output_tokens=128000)


def _developer(text):
    return {"role": "developer", "content": [{"type": "input_text", "text": text}]}


def _user(text):
    return {"role": "user", "content": [{"type": "input_text", "text": text}]}


def _assistant(text):
    return {"role": "assistant", "content": [{"type": "output_text", "text": text}]}


def _system_turn(text):
    return {"role": "system", "content": [{"type": "text", "text": text}]}


def _call(call_id):
    return {"type": "function_call", "call_id": call_id, "name": "shell", "arguments": "{}"}


def _output(call_id):
    return {"type": "function_call_output", "call_id": call_id, "output": "ok"}


def test_leading_developer_messages_stay_in_the_system_prompt():
    body = project(request(instructions="Base", input=[_developer("Rules"), _user("Hi")]), max_output_tokens=64000).body
    assert body["system"] == [{"type": "text", "text": "Base"}, {"type": "text", "text": "Rules"}]
    assert [message["role"] for message in body["messages"]] == ["user"]


def test_later_developer_messages_keep_their_position_after_the_next_user_turn():
    history = [_user("Hi"), _assistant("Hello"), _developer("Sandbox changed"), _user("Next")]
    body = project(request(input=history), max_output_tokens=64000).body
    assert "system" not in body
    assert body["messages"][2:] == [
        {"role": "user", "content": [{"type": "text", "text": "Next"}]},
        _system_turn("Sandbox changed"),
    ]
    # The next request extends the same prefix: the system turn stays ahead of the answer.
    later = project(request(input=[*history, _assistant("Done"), _user("More")]), max_output_tokens=64000).body
    assert later["messages"][:4] == body["messages"]
    assert [message["role"] for message in later["messages"][4:]] == ["assistant", "user"]


def test_developer_message_after_a_tool_result_precedes_the_next_assistant_turn():
    history = [_user("Hi"), _call("c1"), _output("c1"), _developer("Approved"), _call("c2"), _output("c2")]
    body = project(request(input=history), max_output_tokens=64000).body
    assert [message["role"] for message in body["messages"]] == [
        "user",
        "assistant",
        "user",
        "system",
        "assistant",
        "user",
    ]
    assert body["messages"][3] == _system_turn("Approved")


def test_developer_message_between_assistant_items_waits_for_a_user_turn():
    history = [_user("Hi"), _assistant("Looking"), _developer("Note"), _call("c1"), _output("c1")]
    body = project(request(input=history), max_output_tokens=64000).body
    assert [message["role"] for message in body["messages"]] == ["user", "assistant", "user", "system"]


def test_developer_message_after_an_assistant_tail_follows_the_continuation():
    body = project(request(input=[_user("Hi"), _assistant("Partial"), _developer("Note")]), max_output_tokens=64000)
    assert body.body["messages"][2:] == [
        {"role": "user", "content": [{"type": "text", "text": "(continue)"}]},
        _system_turn("Note"),
    ]


def test_models_without_system_turns_close_the_user_turn_with_a_reminder():
    history = [_user("Hi"), _assistant("Hello"), _developer("Sandbox changed"), _user("Next")]
    body = project(request(model="anthropic/claude-haiku-4-5-20251001", input=history), max_output_tokens=64000).body
    assert [message["role"] for message in body["messages"]] == ["user", "assistant", "user"]
    assert body["messages"][2]["content"] == [
        {"type": "text", "text": "Next"},
        {"type": "text", "text": "<system-reminder>"},
        {"type": "text", "text": "Sandbox changed"},
        {"type": "text", "text": "</system-reminder>"},
    ]


@pytest.mark.parametrize("reasoning", [None, {"effort": "high"}])
def test_null_sampling_controls_are_absent(reasoning):
    body = project(
        request(temperature=None, top_p=None, **({"reasoning": reasoning} if reasoning else {})),
        max_output_tokens=64000,
    ).body
    assert "temperature" not in body
    assert "top_p" not in body


@pytest.mark.parametrize(
    "levels,requested,sent",
    [
        (("low", "medium", "high", "xhigh", "max"), "xhigh", "xhigh"),
        (("low", "medium", "high", "max"), "xhigh", "high"),
        (("low", "medium", "high"), "max", "high"),
        (("low", "medium", "high", "max"), "max", "max"),
    ],
)
def test_adaptive_effort_is_forwarded_or_stepped_down_never_escalated(levels, requested, sent):
    spec = ReasoningSpec(mode="adaptive", levels=levels, default="high")
    body = project_responses(request(reasoning={"effort": requested}), max_output_tokens=64000, reasoning=spec).body
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": sent}


def test_reasoning_is_rejected_for_a_model_without_reasoning_capability():
    with pytest.raises(ClientPayloadError):
        project_responses(request(reasoning={"effort": "high"}), max_output_tokens=64000, reasoning=None)


LOOKUP_TOOL = {"type": "function", "name": "lookup", "parameters": {"type": "object", "properties": {}}}


@pytest.mark.parametrize(
    "choice,sent",
    [
        ({"type": "none"}, {"type": "none"}),
        ({"type": "auto"}, {"type": "auto", "disable_parallel_tool_use": True}),
        ({"type": "required"}, {"type": "any", "disable_parallel_tool_use": True}),
        ("none", {"type": "none"}),
    ],
)
def test_tool_choice_directives_keep_declarations_and_scope_parallel_control(choice, sent):
    body = project(
        request(tools=[LOOKUP_TOOL], tool_choice=choice, parallel_tool_calls=False), max_output_tokens=64000
    ).body
    assert body["tool_choice"] == sent
    assert len(body["tools"]) == 1


@pytest.mark.parametrize("choice", [{"type": "none"}, "none", {"type": "auto"}])
def test_unforced_tool_choice_directives_combine_with_thinking(choice):
    body = project(
        request(tools=[LOOKUP_TOOL], tool_choice=choice, reasoning={"effort": "high"}), max_output_tokens=64000
    ).body
    assert body["thinking"] == {"type": "adaptive"}


@pytest.mark.parametrize("choice", [{"type": "required"}, {"type": "function", "name": "lookup"}])
def test_forced_tool_choice_still_rejects_thinking(choice):
    with pytest.raises(ClientPayloadError, match="forced tool choice"):
        project(request(tools=[LOOKUP_TOOL], tool_choice=choice, reasoning={"effort": "high"}), max_output_tokens=64000)


def test_tool_choice_directive_with_extra_fields_is_rejected():
    with pytest.raises(ClientPayloadError, match="Unsupported tool choice"):
        project(request(tools=[LOOKUP_TOOL], tool_choice={"type": "none", "name": "lookup"}), max_output_tokens=64000)


def test_structured_output_and_reasoning_share_output_configuration():
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    result = project(
        request(text={"format": {"type": "json_schema", "schema": schema}}, reasoning={"effort": "high"}),
        max_output_tokens=8192,
    )
    assert result.body["output_config"] == {"effort": "high", "format": {"type": "json_schema", "schema": schema}}


@pytest.mark.parametrize("model", ["claude-haiku-4-5-20251001", "claude-sonnet-4-5-20250929"])
def test_budget_thinking_is_bounded_by_caller_output_limit(model):
    result = project(
        request(model=f"anthropic/{model}", reasoning={"effort": "medium"}, max_output_tokens=10000),
        max_output_tokens=64000,
    )
    assert result.body["thinking"] == {"type": "enabled", "budget_tokens": 8192}
    assert result.body["max_tokens"] == 10000
    assert "output_config" not in result.body
    with pytest.raises(ClientPayloadError):
        project(
            request(model=f"anthropic/{model}", reasoning={"effort": "medium"}, max_output_tokens=8192),
            max_output_tokens=64000,
        )


HAIKU = "anthropic/claude-haiku-4-5-20251001"
SIGNED = {"type": "thinking", "thinking": "plan", "signature": "sig"}


def tool_loop(*, signed=False, commentary=False, ending="tool"):
    items = [{"role": "user", "content": "inspect"}]
    if signed:
        items.append({"type": "reasoning", "encrypted_content": "signed"})
    if commentary:
        items.append({"role": "assistant", "content": "Looking"})
    items += [
        {"type": "function_call", "name": "read", "call_id": "call", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call", "output": "ok"},
    ]
    if ending in ("answer", "assistant"):
        items.append({"role": "assistant", "content": "Done"})
    if ending in ("answer", "merged_user"):
        items.append({"role": "user", "content": "next"})
    return {
        "model": HAIKU,
        "input": items,
        "tools": [{"type": "function", "name": "read", "parameters": {"type": "object"}}],
        "reasoning": {"effort": "medium"},
    }


@pytest.mark.parametrize(
    "loop",
    [{}, {"commentary": True}, {"ending": "merged_user"}],
    ids=["tool_output", "commentary", "user_text_joins_tool_result_message"],
)
def test_budget_thinking_is_disabled_for_unsigned_open_tool_turn(caplog, loop):
    payload = tool_loop(**loop)
    payload["temperature"] = 0.2
    with caplog.at_level("INFO"):
        result = project(payload, max_output_tokens=64000)
    assert result.body["thinking"] == {"type": "disabled"}
    assert result.body["temperature"] == 0.2
    assert "reason=unsigned_open_turn" in caplog.text
    with pytest.raises(ClientPayloadError, match="Unsupported Claude reasoning effort"):
        project({**payload, "reasoning": {"effort": "extreme"}}, max_output_tokens=64000)
    with pytest.raises(ClientPayloadError, match="below max_output_tokens"):
        project({**payload, "max_output_tokens": 8192}, max_output_tokens=64000)


@pytest.mark.parametrize(
    "loop",
    [
        {"signed": True},
        {"ending": "answer"},
        {"ending": "assistant"},
    ],
    ids=["signed_turn", "new_user_turn", "continuation_turn"],
)
def test_budget_thinking_stays_enabled_outside_unsigned_open_turns(loop):
    result = project(tool_loop(**loop), max_output_tokens=64000, restore_reasoning=lambda token: dict(SIGNED))
    assert result.body["thinking"] == {"type": "enabled", "budget_tokens": 8192}


def test_adaptive_thinking_is_unchanged_for_unsigned_open_tool_turn():
    result = project({**tool_loop(), "model": "anthropic/claude-opus-5"}, max_output_tokens=64000)
    assert result.body["thinking"] == {"type": "adaptive"}


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "anthropic/claude-opus-5-99", "reasoning": {"effort": "high"}},
        {"service_tier": "priority"},
        {"truncation": "auto"},
        {"tools": [{"type": "custom", "name": "grammar", "format": {"type": "grammar", "definition": "x"}}]},
        {
            "tools": [
                {
                    "type": "custom",
                    "name": "grammar",
                    "format": {"type": "grammar", "syntax": "ebnf", "definition": "x"},
                }
            ]
        },
        {"tools": [{"type": "custom", "name": "grammar", "format": {"type": "grammar", "syntax": "lark"}}]},
        {"tools": [{"type": "custom", "name": "grammar", "format": {"type": "json"}}]},
    ],
)
def test_unsupported_semantics_are_not_silently_dropped(payload):
    with pytest.raises(ClientPayloadError):
        project(request(**payload), max_output_tokens=8192)


APPLY_PATCH_GRAMMAR = 'start: begin_patch hunk+ end_patch\nbegin_patch: "*** Begin Patch" LF\n'


def apply_patch_tool():
    return {
        "type": "custom",
        "name": "apply_patch",
        "description": "Edit files.",
        "format": {"type": "grammar", "syntax": "lark", "definition": APPLY_PATCH_GRAMMAR},
    }


def test_grammar_custom_tool_documents_its_grammar_on_the_raw_input():
    projected = project(request(tools=[apply_patch_tool()]), max_output_tokens=8192)
    [declaration] = array(projected.body["tools"])
    assert at(declaration, "description") == "Edit files."
    schema = at(declaration, "input_schema")
    assert at(schema, "required") == ["input"]
    assert at(schema, "additionalProperties") is False
    description = at(schema, "properties", "input", "description")
    assert isinstance(description, str)
    assert description.endswith(f"It must match this lark grammar:\n{APPLY_PATCH_GRAMMAR}")
    [identity] = projected.tools.by_wire.values()
    assert (identity.name, identity.namespace, identity.custom) == ("apply_patch", None, True)


def test_text_custom_tool_input_carries_no_grammar():
    projected = project(
        request(tools=[{"type": "custom", "name": "exec", "format": {"type": "text"}}]), max_output_tokens=8192
    )
    [declaration] = array(projected.body["tools"])
    assert at(declaration, "input_schema", "properties", "input", "description") == (
        "Raw text passed verbatim to the tool."
    )


def test_apply_patch_call_roundtrips_as_custom_tool_call():
    patch = "*** Begin Patch\n*** Add File: a.txt\n+a\n*** End Patch\n"
    payload = request(tools=[apply_patch_tool()])
    projected = project(payload, max_output_tokens=8192)
    wire = next(iter(projected.tools.by_wire))
    response = ResponsesProjection(scope(), projected.tools, codec()).complete(
        {
            "id": "msg1",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "content": [{"type": "tool_use", "id": "call1", "name": wire, "input": {"input": patch}}],
        }
    )
    call = at(response, "output", -1)
    assert isinstance(call, dict)
    assert (call["type"], call["name"], call["input"]) == ("custom_tool_call", "apply_patch", patch)
    history = [
        {"role": "user", "content": "Hello"},
        *array(response["output"]),
        {"type": "custom_tool_call_output", "call_id": "call1", "output": "Success. Updated a.txt"},
    ]
    replay = project(request(tools=payload["tools"], input=history), max_output_tokens=8192)
    assert at(replay.body, "messages", 1, "content", 0, "input") == {"input": patch}
    assert at(replay.body, "messages", 2, "content", 0, "tool_use_id") == "call1"


def scope():
    return OpaqueScope("source-a", "anthropic/claude-opus-5", "key-a")


def codec():
    return ClaudeOpaqueState(TokenEncryptor(key=Fernet.generate_key()))


@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("model", ["anthropic/claude-opus-5", "anthropic/claude-opus-5-5"])
def test_assistant_tail_preserves_history_and_appends_wire_only_continuation(signed, model):
    opaque = codec()
    block = {"type": "thinking", "thinking": "preserve", "signature": "signed"}
    history = [{"role": "user", "content": "Hello"}]
    if signed:
        history.append({"type": "reasoning", "encrypted_content": opaque.encode(scope(), block)})
    history.append({"role": "assistant", "content": [{"type": "output_text", "text": "Progress"}]})
    payload = request(input=history, model=model)
    original = deepcopy(payload)
    projected = project(
        payload,
        max_output_tokens=8192,
        restore_reasoning=lambda token: (
            opaque.decode(token, model=scope().model, client_scope=scope().client_scope).block
        ),
    )
    assert projected.body["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
        {"role": "assistant", "content": ([block] if signed else []) + [{"type": "text", "text": "Progress"}]},
        {"role": "user", "content": [{"type": "text", "text": "(continue)"}]},
    ]
    assert payload == original


def test_reasoning_only_tail_gets_continuation_without_losing_summary():
    body = project(
        request(input=[{"type": "reasoning", "summary": [{"type": "summary_text", "text": "Preserve reason"}]}]),
        max_output_tokens=8192,
    ).body
    assert body["messages"][-1] == {"role": "user", "content": [{"type": "text", "text": "(continue)"}]}
    assert "Preserve reason" in json.dumps(body["messages"][0])


@pytest.mark.parametrize("result", [False, True])
def test_user_or_tool_result_tail_needs_no_synthetic_continuation(result):
    history = [{"role": "user", "content": "Hello"}]
    if result:
        history.extend(
            [
                {"type": "function_call", "name": "run", "call_id": "call1", "arguments": "{}"},
                {"type": "function_call_output", "call_id": "call1", "output": "done"},
            ]
        )
    body = project(request(input=history), max_output_tokens=8192).body
    assert body["messages"][-1]["role"] == "user"
    assert "(continue)" not in json.dumps(body)


def test_continuation_never_supplies_a_missing_tool_result():
    history = [
        {"role": "user", "content": "Hello"},
        {"type": "function_call", "name": "run", "call_id": "call1", "arguments": "{}"},
        {"role": "assistant", "content": "Progress"},
    ]
    with pytest.raises(ClientPayloadError, match="require their outputs"):
        project(request(input=history), max_output_tokens=8192)


@pytest.mark.parametrize("name", ["unknown_tool", "bad\nprivate-name", "a" * 129, "\ud800"])
def test_undeclared_tool_is_rejected_with_bounded_content_free_diagnostics(caplog, name):
    adapter = ResponsesProjection(scope(), ClaudeToolNames(), codec())
    adapter.consume({"type": "message_start", "message": {"id": "msg_fixture", "usage": {}}})
    with pytest.raises(ClaudeError, match="undeclared tool"):
        adapter.consume(
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "tool_use",
                    "id": "private-call",
                    "name": name,
                    "input": {"secret": "private-argument"},
                },
            }
        )
    assert "claude_undeclared_tool source_id=source-a" in caplog.text
    assert "content_index=0 declared_count=0" in caplog.text
    assert "tool_name_hash=" in caplog.text
    assert "private-call" not in caplog.text and "private-argument" not in caplog.text
    if name == "unknown_tool":
        assert "tool_name=unknown_tool" in caplog.text
    else:
        assert "tool_name=None" in caplog.text
        assert name not in caplog.text


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
    projected = project(payload, max_output_tokens=8192)
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
    projected = project(payload, max_output_tokens=8192)
    wire = next(iter(projected.tools.by_wire))
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
    replay = project(
        request(tools=payload["tools"], input=history),
        max_output_tokens=8192,
        restore_reasoning=lambda token: (
            opaque.decode(token, model=scope().model, client_scope=scope().client_scope).block
        ),
    )
    assert at(replay.body, "messages", 1, "content") == [
        {"type": "thinking", "thinking": "preserve", "signature": "signed"},
        {"type": "text", "text": "Run tool"},
        {"type": "tool_use", "id": "call1", "name": wire, "input": {"input": "hello\nworld"}},
    ]
    assert at(replay.body, "messages", 2, "content", 0, "tool_use_id") == "call1"


@pytest.mark.parametrize("field,value", [("model", "anthropic/claude-sonnet-5"), ("client_scope", "key-b")])
def test_opaque_state_cannot_cross_scope(field, value):
    opaque = codec()
    token = opaque.encode(scope(), {"type": "redacted_thinking", "data": "opaque"})
    args = {
        "model": scope().model,
        "client_scope": scope().client_scope,
        field: value,
    }
    with pytest.raises(ClientPayloadError):
        opaque.decode(token, **args)


COLLABORATION_TOOLS: list[JsonValue] = [
    {
        "type": "namespace",
        "name": "collaboration",
        "tools": [
            {
                "type": "function",
                "name": "spawn_agent",
                "parameters": {
                    "type": "object",
                    "properties": {"message": {"type": "string", "encrypted": True}},
                    "required": ["message"],
                },
            }
        ],
    },
    {"type": "function", "name": "read", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}},
]


def _wire_names(projected) -> dict[str, str]:
    return {identity.name: wire for wire, identity in projected.tools.by_wire.items()}


def test_translated_calls_to_encrypted_parameter_tools_declare_plaintext():
    projected = project(request(tools=COLLABORATION_TOOLS), max_output_tokens=8192)
    wires = _wire_names(projected)
    response = ResponsesProjection(scope(), projected.tools, codec()).complete(
        {
            "id": "m",
            "stop_reason": "tool_use",
            "usage": {},
            "content": [
                {"type": "tool_use", "id": "a", "name": wires["spawn_agent"], "input": {"message": "Build it"}},
                {"type": "tool_use", "id": "b", "name": wires["read"], "input": {"path": "x"}},
            ],
        }
    )
    spawn, read = array(response["output"])
    assert isinstance(spawn, dict) and isinstance(read, dict)
    assert (spawn["namespace"], spawn["name"], spawn["encrypted_function_args"]) == ("collaboration", "spawn_agent", [])
    assert json.loads(str(spawn["arguments"])) == {"message": "Build it"}
    assert "encrypted_function_args" not in read


def test_streamed_translated_call_declares_plaintext_on_every_item():
    projected = project(request(tools=COLLABORATION_TOOLS), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    events: list[dict[str, JsonValue]] = []
    block = {"type": "tool_use", "id": "a", "name": _wire_names(projected)["spawn_agent"], "input": {}}
    for event in [
        {"type": "message_start", "message": {"id": "m", "usage": {}}},
        {"type": "content_block_start", "index": 0, "content_block": block},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "input_json_delta", "partial_json": '{"message"'},
        },
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": ':"Go"}'}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {}},
        {"type": "message_stop"},
    ]:
        events.extend(adapter.consume(event))
    items = [event["item"] for event in events if event["type"].startswith("response.output_item.")]
    items.append(at(events[-1], "response", "output", 0))
    assert len(items) == 3
    assert all(isinstance(item, dict) and item["encrypted_function_args"] == [] for item in items)


def _stream_tool_call(tools, *fragments):
    projected = project(request(tools=tools), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    block = {"type": "tool_use", "id": "call", "name": next(iter(projected.tools.by_wire)), "input": {}}
    events = adapter.consume({"type": "message_start", "message": {"id": "m", "usage": {}}})
    events += adapter.consume({"type": "content_block_start", "index": 0, "content_block": block})
    for fragment in fragments:
        events += adapter.consume(
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": fragment}}
        )
    events += adapter.consume({"type": "content_block_stop", "index": 0})
    events += adapter.consume({"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {}})
    events += adapter.consume({"type": "message_stop"})
    return events


NO_ARGUMENT_TOOL = [{"type": "function", "name": "list_agents", "parameters": {"type": "object", "properties": {}}}]


def test_streamed_function_call_without_arguments_keeps_start_input():
    events = _stream_tool_call(NO_ARGUMENT_TOOL, "")
    assert not [event for event in events if event["type"] == "response.function_call_arguments.delta"]
    done = next(event for event in events if event["type"] == "response.function_call_arguments.done")
    item = at(events[-1], "response", "output", 0)
    assert done["arguments"] == at(item, "arguments") == "{}"
    assert (at(item, "type"), at(item, "name"), at(item, "status")) == ("function_call", "list_agents", "completed")


def test_streamed_custom_call_without_input_keeps_start_input():
    events = _stream_tool_call([{"type": "custom", "name": "exec", "description": "Run input"}], "")
    item = at(events[-1], "response", "output", 0)
    assert (at(item, "type"), at(item, "input")) == ("custom_tool_call", "")


@pytest.mark.parametrize("fragments", [("{",), ('{"a":', ""), (" ",)])
def test_streamed_malformed_tool_json_fails(fragments):
    with pytest.raises(ClaudeError, match="invalid tool JSON"):
        _stream_tool_call(NO_ARGUMENT_TOOL, *fragments)


@pytest.mark.parametrize(
    "stop,status,reason",
    [
        ("end_turn", "completed", None),
        ("tool_use", "completed", None),
        ("max_tokens", "incomplete", "max_output_tokens"),
        ("pause_turn", "incomplete", "max_output_tokens"),
        ("model_context_window_exceeded", "incomplete", "max_output_tokens"),
        ("refusal", "failed", None),
    ],
)
@pytest.mark.parametrize("chat_reasoning", [False, True])
def test_terminal_semantics(stop, status, reason, chat_reasoning):
    response = ResponsesProjection(scope(), ClaudeToolNames(), codec(), chat_reasoning=chat_reasoning).complete(
        {
            "id": "m",
            "content": [{"type": "text", "text": "answer"}],
            "stop_reason": stop,
            "usage": {"output_tokens": 3},
        }
    )
    assert response["status"] == status
    assert response["incomplete_details"] == (None if reason is None else {"reason": reason})
    assert response["error"] == (
        {
            "code": "invalid_prompt",
            "message": "Claude's safeguards declined this request. "
            "Edit or rephrase your last message, or continue with a different model.",
        }
        if stop == "refusal"
        else None
    )
    assert at(response, "output", 0, "content", 0, "text") == "answer"
    assert at(response, "usage", "output_tokens") == 3


def test_streamed_refusal_fails_as_prompt_policy_and_stop_log_has_counts_only(caplog):
    adapter = ResponsesProjection(scope(), ClaudeToolNames(), codec())
    native_events: list[dict[str, JsonValue]] = [
        {"type": "message_start", "message": {"id": "m", "usage": {"input_tokens": 5}}},
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking", "thinking": "", "signature": ""},
        },
        {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "secret plan"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "sig"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "private words"}},
        {"type": "content_block_stop", "index": 1},
        {"type": "message_delta", "delta": {"stop_reason": "refusal"}, "usage": {"output_tokens": 7}},
        {"type": "message_stop"},
    ]
    events = []
    with caplog.at_level(logging.INFO, logger="app.modules.claude.responses"):
        for event in native_events:
            events.extend(adapter.consume(event))
    assert events[-1]["type"] == "response.failed"
    assert at(events[-1], "response", "error", "code") == "invalid_prompt"
    assert at(events[-1], "response", "incomplete_details") is None
    assert at(events[-1], "response", "usage", "output_tokens") == 7
    [line] = [record.getMessage() for record in caplog.records if "claude_message_stop" in record.getMessage()]
    assert "response_id=resp_m" in line
    assert "stop_reason=refusal status=failed blocks=text:1,thinking:1 output_tokens=7" in line
    assert "secret" not in line and "private" not in line and "sig" not in line


def _open_tool_stream(stop_reason: str | None) -> tuple[ResponsesProjection, list[dict[str, JsonValue]]]:
    projected = project(request(tools=NO_ARGUMENT_TOOL), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    tool: dict[str, JsonValue] = {
        "type": "tool_use",
        "id": "call",
        "name": next(iter(projected.tools.by_wire)),
        "input": {},
    }
    stream: list[dict[str, JsonValue]] = [
        {"type": "message_start", "message": {"id": "m", "usage": {}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Running"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": tool},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"a'}},
    ]
    if stop_reason is not None:
        stream.append({"type": "message_delta", "delta": {"stop_reason": stop_reason}, "usage": {"output_tokens": 4}})
    events = []
    for event in stream:
        events.extend(adapter.consume(event))
    return adapter, events


def test_mid_stream_refusal_discards_the_open_tool_call():
    adapter, events = _open_tool_stream("refusal")
    events.extend(adapter.consume({"type": "message_stop"}))
    terminal = events[-1]
    assert terminal["type"] == "response.failed"
    assert at(terminal, "response", "error", "code") == "invalid_prompt"
    assert at(terminal, "response", "usage", "output_tokens") == 4
    assert [at(item, "type") for item in array(at(terminal, "response", "output"))] == ["message"]
    done = [event for event in events if str(event["type"]).endswith(".done")]
    assert {event.get("output_index") for event in done} == {0}
    assert not [event for event in events if event["type"] == "response.function_call_arguments.done"]


def _completed_tool_stream() -> tuple[ResponsesProjection, list[dict[str, JsonValue]]]:
    projected = project(request(tools=NO_ARGUMENT_TOOL), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    tool: dict[str, JsonValue] = {
        "type": "tool_use",
        "id": "call",
        "name": next(iter(projected.tools.by_wire)),
        "input": {},
    }
    events = []
    stream: list[dict[str, JsonValue]] = [
        {"type": "message_start", "message": {"id": "m", "usage": {}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Running"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": tool},
        {"type": "content_block_stop", "index": 1},
        {"type": "content_block_start", "index": 2, "content_block": {**tool, "id": "second"}},
        {"type": "content_block_stop", "index": 2},
    ]
    for event in stream:
        events.extend(adapter.consume(event))
    return adapter, events


def test_completed_tool_calls_are_released_only_with_a_non_refusal_stop():
    adapter, events = _completed_tool_stream()
    assert [event["output_index"] for event in events if event["type"] == "response.output_item.done"] == [0]
    events.extend(adapter.consume({"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {}}))
    assert [event["output_index"] for event in events if event["type"] == "response.output_item.done"] == [0]
    events.extend(adapter.consume({"type": "message_stop"}))
    assert [event["output_index"] for event in events if event["type"] == "response.output_item.done"] == [0, 1, 2]
    assert [event["sequence_number"] for event in events] == list(range(len(events)))
    assert events[-1]["type"] == "response.completed"
    assert [at(item, "call_id") for item in array(at(events[-1], "response", "output"))[1:]] == ["call", "second"]


def test_refusal_discards_held_tool_calls_and_logs_its_category(caplog):
    adapter, events = _completed_tool_stream()
    with caplog.at_level(logging.INFO, logger="app.modules.claude.responses"):
        events.extend(
            adapter.consume(
                {
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": "refusal",
                        "stop_details": {"type": "refusal", "category": "cyber", "explanation": "private prose"},
                    },
                    "usage": {"output_tokens": 9},
                }
            )
        )
        events.extend(adapter.consume({"type": "message_stop"}))
    assert [event["output_index"] for event in events if event["type"] == "response.output_item.done"] == [0]
    assert not [event for event in events if event["type"] == "response.function_call_arguments.done"]
    assert [event["sequence_number"] for event in events] == list(range(len(events)))
    assert events[-1]["type"] == "response.failed"
    assert at(events[-1], "response", "error") == {
        "code": "invalid_prompt",
        "message": "Claude's safeguards declined this request (cyber). private prose "
        "Edit or rephrase your last message, or continue with a different model.",
    }
    assert [at(item, "type") for item in array(at(events[-1], "response", "output"))] == ["message"]
    assert adapter.refused_delivered_output
    [line] = [record.getMessage() for record in caplog.records if "claude_message_stop" in record.getMessage()]
    assert "refusal_category=cyber withheld=2 delivered_output=True" in line
    assert "private" not in line


@pytest.mark.parametrize(
    "details,category", [({"category": "bio"}, "bio"), ({"category": "a b\n"}, "unrecognized"), (None, None)]
)
def test_refusal_without_delivered_output_needs_no_history_record(caplog, details, category):
    adapter = ResponsesProjection(scope(), ClaudeToolNames(), codec())
    delta: dict[str, JsonValue] = {"stop_reason": "refusal", **({"stop_details": details} if details else {})}
    stream: list[dict[str, JsonValue]] = [
        {"type": "message_start", "message": {"id": "m", "usage": {}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "message_delta", "delta": delta, "usage": {}},
        {"type": "message_stop"},
    ]
    with caplog.at_level(logging.INFO, logger="app.modules.claude.responses"):
        for event in stream:
            adapter.consume(event)
    assert not adapter.refused_delivered_output
    [line] = [record.getMessage() for record in caplog.records if "claude_message_stop" in record.getMessage()]
    assert f"refusal_category={category} withheld=0 delivered_output=False" in line


@pytest.mark.parametrize(
    "stop_reason,message",
    [
        ("end_turn", r"unfinished output \(open=tool_use:1, pending_search=0, stop_reason=end_turn\)"),
        (None, r"unfinished output \(open=tool_use:1, pending_search=0, stop_reason=None\)"),
        ("surprise", "Unknown Claude stop reason surprise"),
    ],
)
def test_unfinished_non_refusal_stop_fails_with_diagnostics(caplog, stop_reason, message):
    adapter, _ = _open_tool_stream(stop_reason)
    with caplog.at_level(logging.INFO, logger="app.modules.claude.responses"):
        with pytest.raises(ClaudeError, match=message):
            adapter.consume({"type": "message_stop"})
    [line] = [record.getMessage() for record in caplog.records if "claude_message_stop" in record.getMessage()]
    assert f"stop_reason={stop_reason} status=invalid blocks=text:1,tool_use:1" in line
    assert "open=tool_use:1 pending_search=0" in line


def test_empty_end_turn_stop_log_records_no_blocks(caplog):
    with caplog.at_level(logging.INFO, logger="app.modules.claude.responses"):
        response = ResponsesProjection(scope(), ClaudeToolNames(), codec()).complete(
            {"id": "m", "content": [], "stop_reason": "end_turn", "usage": {"output_tokens": 0}}
        )
    assert response["status"] == "completed"
    assert any(
        "stop_reason=end_turn status=completed blocks=none output_tokens=0" in record.getMessage()
        for record in caplog.records
    )


def test_stream_lifecycle_and_signature_deltas():
    opaque = codec()
    adapter = ResponsesProjection(scope(), ClaudeToolNames(), opaque)
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
    adapter = ResponsesProjection(scope(), ClaudeToolNames(), codec())
    adapter.consume({"type": "message_start", "message": {"id": "m"}})
    with pytest.raises(ClaudeError):
        adapter.consume({"type": "message_stop"})
    assert not adapter.stopped


@pytest.mark.parametrize(
    "item",
    [
        {"type": "function_call_output", "call_id": "", "output": "result"},
        {"type": "item_reference", "id": "missing"},
        {"role": "user", "content": [{"type": "input_image", "image_url": "file:///private"}]},
    ],
)
def test_unsupported_or_malformed_history_rejected(item):
    with pytest.raises(ClientPayloadError):
        project(request(input=[item]), max_output_tokens=8192)


@pytest.mark.parametrize("kind", ["function_call_output", "custom_tool_call_output"])
@pytest.mark.parametrize(
    "output",
    [
        "delegated context",
        "",
        [
            {"type": "input_text", "text": "image context"},
            {"type": "input_image", "image_url": "data:image/png;base64,aW1hZ2U="},
        ],
    ],
)
def test_standalone_tool_output_is_labeled_context_and_preserves_logical_history(kind, output):
    payload = request(
        input=[
            {"type": kind, "call_id": "delegation-seed", "output": output},
            {"role": "user", "content": "Continue"},
        ]
    )
    original = deepcopy(payload)
    body = project(payload, max_output_tokens=8192).body
    blocks = body["messages"][0]["content"]
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "user"
    assert blocks[0] == {"type": "text", "text": f"[Standalone {kind}: call_id=delegation-seed]"}
    if isinstance(output, str):
        assert blocks[1] == {"type": "text", "text": output}
    else:
        assert blocks[1:3] == [
            {"type": "text", "text": "image context"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "aW1hZ2U="}},
        ]
    assert blocks[-1] == {"type": "text", "text": "Continue"}
    assert payload == original


@pytest.mark.parametrize(
    "case,reason",
    [
        ("duplicate", "duplicate_result"),
        ("out_of_order", "out_of_order_result"),
        ("interrupted", "interrupted_tool_cycle"),
        ("invalid", "invalid_call_id"),
    ],
)
def test_bad_tool_output_cycles_fail_with_content_free_diagnostics(caplog, case, reason):
    from app.core.utils.request_id import reset_request_id, set_request_id

    call = {"type": "function_call", "call_id": "private-call-id", "name": "run", "arguments": "{}"}
    result = {"type": "function_call_output", "call_id": "private-call-id", "output": "private-tool-content"}
    items = {
        "duplicate": [call, result, result],
        "out_of_order": [result, call],
        "interrupted": [call, {**result, "call_id": "standalone-id"}],
        "invalid": [{**result, "call_id": None}],
    }[case]
    token = set_request_id("request-fixture")
    try:
        with pytest.raises(ClientPayloadError, match=reason) as error:
            project(request(input=items), max_output_tokens=8192)
    finally:
        reset_request_id(token)
    assert error.value.param == f"input[{len(items) - 1 if case != 'out_of_order' else 0}].call_id"
    assert "request_id=request-fixture" in caplog.text
    assert f"reason={reason}" in caplog.text
    assert "item_index=" in caplog.text and "pending_count=" in caplog.text and "call_id_hash=" in caplog.text
    assert "private-call-id" not in caplog.text
    assert "private-tool-content" not in caplog.text
    assert "standalone-id" not in caplog.text


def test_standalone_context_does_not_change_subsequent_parallel_tool_pairs():
    payload = request(
        input=[
            {"type": "custom_tool_call_output", "call_id": "seed", "output": "delegation context"},
            {"type": "function_call", "call_id": "a", "name": "run", "arguments": "{}"},
            {"type": "function_call", "call_id": "b", "name": "run", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "b", "output": "B"},
            {"type": "function_call_output", "call_id": "a", "output": "A"},
        ]
    )
    messages = project(payload, max_output_tokens=8192).body["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant", "user"]
    assert [block["id"] for block in messages[1]["content"]] == ["a", "b"]
    assert [block["tool_use_id"] for block in messages[2]["content"]] == ["b", "a"]


def test_standalone_output_does_not_complete_a_pending_call():
    with pytest.raises(ClientPayloadError, match="Tool results are required"):
        project(
            request(
                input=[
                    {"type": "function_call_output", "call_id": "seed", "output": "context"},
                    {"type": "function_call", "call_id": "active", "name": "run", "arguments": "{}"},
                    {"role": "user", "content": "Continue"},
                ]
            ),
            max_output_tokens=8192,
        )


TASK_INPUT = {
    "type": "function_call_output",
    "id": "fc_task",
    "name": "create_thread",
    "namespace": "codex",
    "output": "Delegated task context",
}


@pytest.mark.parametrize("pairing", [{}, {"call_id": None}, {"call_id": ""}, {"call_id": " \t"}])
@pytest.mark.parametrize("established", [False, True])
def test_external_task_input_is_user_content_without_mutating_history(pairing, established):
    items = [{"role": "assistant", "content": "Earlier answer"}] if established else []
    payload = request(input=[*items, {**TASK_INPUT, **pairing}])
    original = deepcopy(payload)
    messages = project(payload, max_output_tokens=8192).body["messages"]
    assert messages[-1] == {"role": "user", "content": [{"type": "text", "text": TASK_INPUT["output"]}]}
    assert payload == original


def test_external_task_preserves_every_text_and_image_block_in_order():
    task = {
        **TASK_INPUT,
        "call_id": None,
        "output": [
            {"type": "output_text", "text": "before"},
            {"type": "text", "text": ""},
            {"type": "input_image", "image_url": "data:image/png;base64,aW1hZ2U=", "detail": "original"},
            {"type": "input_text", "text": "after"},
        ],
    }
    original = deepcopy(task)
    messages = project(request(input=[task]), max_output_tokens=8192).body["messages"]
    assert messages == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "before"},
                {"type": "text", "text": ""},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "aW1hZ2U="}},
                {"type": "text", "text": "after"},
            ],
        }
    ]
    assert task == original


@pytest.mark.parametrize(
    "overrides",
    [
        {"call_id": 1},
        {"call_id": {}},
        {"call_id": False},
        {"type": "custom_tool_call_output"},
        {"id": None},
        {"name": ""},
        {"namespace": " "},
        {"output": "\t"},
        {"output": []},
        {"output": [{"type": "text", "text": " "}]},
        {"output": [{"type": "text", "text": 1}]},
        {"output": [{"type": "text", "text": "keep"}, {"type": "unknown", "text": "do not drop"}]},
        {"output": [{"type": "input_image", "image_url": ""}]},
        {"output": [{"type": "input_image", "image_url": "https://example.com/a.png", "detail": None}]},
        {"output": [{"type": "input_image", "image_url": "https://example.com/a.png", "detail": "invalid"}]},
    ],
)
def test_incomplete_or_malformed_task_is_not_a_repaired_tool_result(overrides, caplog):
    with pytest.raises(ClientPayloadError, match="invalid_call_id"):
        project(request(input=[{**TASK_INPUT, **overrides}]), max_output_tokens=8192)
    assert "call_id_type=" in caplog.text and "task_metadata_complete=" in caplog.text
    for private in ("fc_task", "create_thread", "Delegated task context", "do not drop"):
        assert private not in caplog.text


@pytest.mark.parametrize("field", ["id", "name", "namespace"])
def test_external_task_requires_all_metadata_fields(field):
    task = {key: value for key, value in TASK_INPUT.items() if key != field}
    with pytest.raises(ClientPayloadError, match="invalid_call_id"):
        project(request(input=[task]), max_output_tokens=8192)


@pytest.mark.parametrize(
    "url", ["file:///private/image.png", "data:image/png;base64,invalid!", "data:image/svg+xml;base64,aW1hZ2U="]
)
def test_external_task_still_requires_valid_claude_images(url):
    task = {**TASK_INPUT, "output": [{"type": "input_image", "image_url": url}]}
    with pytest.raises(ClientPayloadError):
        project(request(input=[task]), max_output_tokens=8192)


def test_external_task_cannot_interrupt_a_pending_tool_cycle():
    call = {"type": "function_call", "call_id": "active", "name": "run", "arguments": "{}"}
    with pytest.raises(ClientPayloadError, match="interrupted_tool_cycle"):
        project(request(input=[call, TASK_INPUT]), max_output_tokens=8192)
    result = {"type": "function_call_output", "call_id": "active", "output": "result"}
    messages = project(request(input=[call, result, TASK_INPUT]), max_output_tokens=8192).body["messages"]
    assert messages[-1]["content"] == [
        {"type": "tool_result", "tool_use_id": "active", "content": [{"type": "text", "text": "result"}]},
        {"type": "text", "text": TASK_INPUT["output"]},
    ]


def test_real_pairing_key_does_not_become_external_task_input():
    call = {"type": "function_call", "call_id": "active", "name": "run", "arguments": "{}"}
    result = {**TASK_INPUT, "call_id": "active"}
    messages = project(request(input=[call, result]), max_output_tokens=8192).body["messages"]
    assert messages[-1]["content"] == [
        {"type": "tool_result", "tool_use_id": "active", "content": [{"type": "text", "text": TASK_INPUT["output"]}]}
    ]
