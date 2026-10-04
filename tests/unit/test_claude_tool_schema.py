import copy
import json

import pytest
from jsonschema import Draft202012Validator

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude import tool_schema
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.protocol import project_responses
from app.modules.claude.responses import ResponsesProjection
from app.modules.claude.tool_schema import adapt_tool_schema
from tests.unit.test_claude_protocol import codec, request, scope

pytestmark = pytest.mark.unit


def project(payload, **kwargs):
    """Project with the policy-derived reasoning the payload's model would get."""
    return project_responses(payload, reasoning=reasoning_spec(str(payload.get("model", "")), None), **kwargs)


MODES = {
    "oneOf": [
        {
            "type": "object",
            "properties": {"mode": {"const": "view"}, "id": {"type": "string"}},
            "required": ["mode", "id"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {"mode": {"const": "update"}, "prompt": {"type": "string"}},
            "required": ["mode", "prompt"],
            "additionalProperties": False,
        },
    ],
}


def adapt(schema):
    return adapt_tool_schema(schema, tool_name="codex_app.automation_update", param="tools[0].tools[0].parameters")


def declaration(schema=MODES):
    return [
        {
            "type": "namespace",
            "name": "codex_app",
            "tools": [
                {"type": "function", "name": "automation_update", "parameters": schema},
            ],
        }
    ]


@pytest.mark.parametrize(
    "schema,values",
    [
        (
            MODES,
            [
                {"mode": "view", "id": "a"},
                {"mode": "update", "prompt": "b"},
                {"mode": "view"},
                {"mode": "view", "prompt": "b"},
                {},
                {"mode": "update", "prompt": "b", "id": "a"},
            ],
        ),
        (
            {"type": "object", "properties": {"a": {}, "b": {}}, "anyOf": [{"required": ["a"]}, {"required": ["b"]}]},
            [{}, {"a": 1}, {"b": 2}, {"a": 1, "b": 2}],
        ),
        (
            {"allOf": [{"properties": {"n": {"minimum": 10}}}, {"properties": {"n": {"maximum": 20}}}]},
            [{"n": 5}, {"n": 15}, {"n": 25}],
        ),
        (
            {"oneOf": [{"properties": {"n": {"minimum": 0}}}, {"properties": {"n": {"maximum": 10}}}]},
            [{"n": -1}, {"n": 5}, {"n": 11}],
        ),
        (
            {
                "allOf": [
                    {"properties": {"a": {}}, "required": ["a"], "additionalProperties": False},
                    {"properties": {"b": {}}, "required": ["b"], "additionalProperties": False},
                ]
            },
            [{"a": 1}, {"b": 1}, {"a": 1, "b": 1}],
        ),
    ],
)
def test_envelope_preserves_schema_semantics(schema, values):
    before = copy.deepcopy(schema)
    wire, arguments = adapt(schema)
    assert arguments is not None
    original = Draft202012Validator(schema)
    transformed = Draft202012Validator(wire)
    assert not {"oneOf", "allOf", "anyOf"} & wire.keys()
    for value in values:
        assert transformed.is_valid({"arguments": value}) == original.is_valid(value)
        if original.is_valid(value):
            assert arguments.decode(arguments.encode(value)) == value
        else:
            with pytest.raises(ClaudeError, match="declared schema"):
                arguments.decode(arguments.encode(value))
    assert schema == before


def test_nested_schema_keywords_and_literal_names_stay_untouched():
    ordinary = {"type": "object", "properties": {"value": {"anyOf": [{"type": "number"}, {"type": "string"}]}}}
    assert adapt(ordinary) == (ordinary, None)
    assert adapt({}) == ({"type": "object", "properties": {}}, None)
    schema = {
        "oneOf": [
            {
                "properties": {
                    "$id": {"type": "string"},
                    "$ref": {"const": "#/$defs/literal"},
                    "value": {"default": {"$ref": "https://literal.invalid", "$id": "literal"}},
                },
            }
        ],
    }
    wire, _ = adapt(schema)
    assert wire["properties"]["arguments"] == schema


@pytest.mark.parametrize("dialect", [None, "http://json-schema.org/draft-07/schema#"])
def test_local_refs_keep_escaped_pointer_and_recursive_root(dialect):
    schema = {
        "$defs": {"a/b~c": {"type": "string"}},
        "anyOf": [
            {
                "type": "object",
                "properties": {"name": {"$ref": "#/$defs/a~1b~0c"}, "child": {"$ref": "#"}},
                "required": ["name"],
                "additionalProperties": False,
            }
        ],
    }
    if dialect:
        schema["$schema"] = dialect
    wire, arguments = adapt(schema)
    relocated = wire["properties"]["arguments"]
    assert relocated["anyOf"][0]["properties"]["child"]["$ref"] == "#/properties/arguments"
    assert relocated["anyOf"][0]["properties"]["name"]["$ref"] == "#/properties/arguments/$defs/a~1b~0c"
    value = {"name": "root", "child": {"name": "nested"}}
    assert Draft202012Validator(wire).is_valid({"arguments": value})
    assert arguments.decode({"arguments": value}) == value


def test_root_reference_gets_enveloped_and_resolves_in_original_document():
    schema = {"$ref": "#/$defs/modes", "$defs": {"modes": MODES}}
    wire, arguments = adapt(schema)
    assert wire["properties"]["arguments"]["$ref"] == "#/properties/arguments/$defs/modes"
    assert Draft202012Validator(wire).is_valid({"arguments": {"mode": "view", "id": "a"}})
    assert arguments.decode({"arguments": {"mode": "view", "id": "a"}}) == {"mode": "view", "id": "a"}


@pytest.mark.parametrize(
    "schema",
    [
        {"oneOf": []},
        {"anyOf": "invalid"},
        {"allOf": [17]},
        {"anyOf": [{}], "$id": "https://example.invalid/schema"},
        {"anyOf": [{"$ref": "https://example.invalid/schema"}]},
        {"anyOf": [{"$ref": "#/missing"}]},
        {"anyOf": [{"$ref": "#anchor"}]},
        {"anyOf": [{"$anchor": "anchor"}]},
        {"anyOf": [{"$ref": "#/default"}], "default": {"type": "object"}},
        {"anyOf": [{"$dynamicRef": "#node"}]},
        {"anyOf": [{"$ref": "#/bad~escape"}]},
        {"anyOf": [{}], "$schema": "https://unknown.invalid/dialect"},
        {"anyOf": [{}], "$schema": {}},
        {"type": "string"},
        {"type": None},
    ],
)
def test_unsupported_schemas_are_named_and_rejected(schema):
    with pytest.raises(ClientPayloadError) as captured:
        adapt(schema)
    assert "codex_app.automation_update" in str(captured.value)
    assert captured.value.param == "tools[0].tools[0].parameters"


def test_schema_budget_limits_are_explicit(monkeypatch):
    monkeypatch.setattr(tool_schema, "MAX_SCHEMA_NODES", 10)
    with pytest.raises(ClientPayloadError, match="complexity"):
        adapt({"anyOf": [{"properties": {str(i): {} for i in range(20)}}]})
    monkeypatch.setattr(tool_schema, "MAX_SCHEMA_NODES", 4096)
    monkeypatch.setattr(tool_schema, "MAX_SCHEMA_DEPTH", 4)
    with pytest.raises(ClientPayloadError, match="complexity"):
        adapt({"anyOf": [{"properties": {"child": {"properties": {"child": {}}}}}]})


@pytest.mark.parametrize("value", [{}, {"arguments": "wrong"}, {"arguments": {}, "extra": True}])
def test_malformed_envelope_fails(value):
    _, arguments = adapt(MODES)
    with pytest.raises(ClaudeError):
        arguments.decode(value)


def test_streamed_envelope_is_private_and_matches_final_and_history():
    tools = declaration()
    payload = request(
        tools=tools, tool_choice={"type": "function", "name": "automation_update", "namespace": "codex_app"}
    )
    projected = project(payload, max_output_tokens=8192)
    wire = next(iter(projected.tools.by_wire))
    assert projected.body["tool_choice"] == {"type": "tool", "name": wire}
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    adapter.consume({"type": "message_start", "message": {"id": "wrapped"}})
    events = adapter.consume(
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "tool_use", "name": wire, "id": "call1", "input": {}},
        }
    )
    arguments = {"mode": "update", "prompt": 'quoted "value" \\ newline\n café'}
    text = json.dumps({"arguments": arguments}, ensure_ascii=False)
    for char in text:
        assert (
            adapter.consume(
                {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": char}}
            )
            == []
        )
    # The completed call is held until the stop reason shows the turn was not refused.
    assert adapter.consume({"type": "content_block_stop", "index": 0}) == []
    adapter.consume({"type": "message_delta", "delta": {"stop_reason": "tool_use"}})
    *released, final = adapter.consume({"type": "message_stop"})
    events += released
    terminal = final["response"]
    delta = next(e["delta"] for e in events if e["type"] == "response.function_call_arguments.delta")
    done = next(e["arguments"] for e in events if e["type"] == "response.function_call_arguments.done")
    item = terminal["output"][0]
    assert json.loads(delta) == arguments
    assert delta == done == item["arguments"]
    assert item["name"] == "automation_update" and item["namespace"] == "codex_app"
    history = [
        {"role": "user", "content": "Go"},
        item,
        {"type": "function_call_output", "call_id": "call1", "output": "ok"},
    ]
    before = copy.deepcopy(history)
    follow = project(request(tools=tools, input=history), max_output_tokens=8192)
    assert follow.body["messages"][1]["content"][0]["input"] == {"arguments": arguments}
    assert history == before
    # Removed or changed declarations reproject logical arguments, never double-wrap.
    for current in ([], declaration({"type": "object"})):
        plain = project(request(tools=current, input=history), max_output_tokens=8192)
        assert plain.body["messages"][1]["content"][0]["input"] == arguments


@pytest.mark.parametrize(
    "raw",
    [
        '{"arguments":',
        '{"arguments":{"mode":"view"}}',
        '{"other":{}}',
        '{"arguments":{"mode":"view","id":"a","id":"b"}}',
        '{"arguments":{"mode":"view","id":"a"},"arguments":{"mode":"view","id":"b"}}',
        '{"arguments":{"mode":"update","prompt":NaN}}',
    ],
)
def test_bad_stream_never_emits_argument_or_done(raw):
    projected = project(request(tools=declaration()), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    adapter.consume({"type": "message_start", "message": {"id": "bad"}})
    adapter.consume(
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "tool_use",
                "name": next(iter(projected.tools.by_wire)),
                "id": "call",
                "input": {},
            },
        }
    )
    assert (
        adapter.consume(
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": raw}}
        )
        == []
    )
    with pytest.raises(ClaudeError):
        adapter.consume({"type": "content_block_stop", "index": 0})
    assert not adapter.stopped


def test_wrapped_stream_without_arguments_fails_envelope_validation():
    projected = project(request(tools=declaration()), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    adapter.consume({"type": "message_start", "message": {"id": "empty"}})
    adapter.consume(
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "tool_use",
                "name": next(iter(projected.tools.by_wire)),
                "id": "call",
                "input": {},
            },
        }
    )
    assert (
        adapter.consume(
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": ""}}
        )
        == []
    )
    with pytest.raises(ClaudeError, match="invalid arguments envelope"):
        adapter.consume({"type": "content_block_stop", "index": 0})


def test_complete_message_unwraps_tool_input():
    projected = project(request(tools=declaration()), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    arguments = {"mode": "view", "id": "item"}
    result = adapter.complete(
        {
            "id": "complete",
            "stop_reason": "tool_use",
            "content": [
                {
                    "type": "tool_use",
                    "id": "call",
                    "name": next(iter(projected.tools.by_wire)),
                    "input": {"arguments": arguments},
                }
            ],
        }
    )
    assert json.loads(result["output"][0]["arguments"]) == arguments


def test_wrapped_argument_buffer_is_bounded(monkeypatch):
    from app.modules.claude import responses

    monkeypatch.setattr(responses, "MAX_TOOL_ARGUMENT_BYTES", 10)
    projected = project(request(tools=declaration()), max_output_tokens=8192)
    adapter = ResponsesProjection(scope(), projected.tools, codec())
    adapter.consume({"type": "message_start", "message": {"id": "big"}})
    adapter.consume(
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "tool_use",
                "name": next(iter(projected.tools.by_wire)),
                "id": "call",
                "input": {},
            },
        }
    )
    with pytest.raises(ClaudeError, match="size limit"):
        adapter.consume(
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "é" * 6}}
        )
    assert not adapter.partial_json
