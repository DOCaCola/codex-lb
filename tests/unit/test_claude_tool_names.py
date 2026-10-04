import json

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import TokenEncryptor
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import project_responses
from app.modules.claude.responses import ResponsesProjection
from app.modules.claude.tool_names import ClaudeToolNames, ToolIdentity, claude_code_name
from tests.claude_json_helpers import array

pytestmark = pytest.mark.unit

_SCHEMA = {"type": "object", "properties": {}}


def _function(name: str) -> dict:
    return {"type": "function", "name": name, "parameters": _SCHEMA}


def _project(**payload):
    body = {"model": "anthropic/claude-opus-5", "input": "Hello", **payload}
    return project_responses(body, reasoning=reasoning_spec("anthropic/claude-opus-5", None), max_output_tokens=8192)


def _adapter(projected) -> ResponsesProjection:
    return ResponsesProjection(
        OpaqueScope("source-a", "anthropic/claude-opus-5", "key-a"),
        projected.tools,
        ClaudeOpaqueState(TokenEncryptor(key=Fernet.generate_key())),
    )


def _called(projected, name: str) -> dict:
    response = _adapter(projected).complete(
        {
            "id": "m",
            "stop_reason": "tool_use",
            "usage": {},
            "content": [{"type": "tool_use", "id": "call", "name": name, "input": {}}],
        }
    )
    [item] = array(response["output"])
    assert isinstance(item, dict)
    return item


@pytest.mark.parametrize(
    "name,wire",
    [
        ("read", "Read"),
        ("bash", "Bash"),
        ("terminal", "Bash"),
        ("read_file", "Read"),
        ("patch", "Edit"),
        ("todo", "TodoWrite"),
        ("apply_patch", "ApplyPatch"),
        ("write_stdin", "WriteStdin"),
        ("view-image", "ViewImage"),
        ("collaboration__spawn_agent", "CollaborationSpawnAgent"),
        ("mcp__github__get_issue", "mcp__github__get_issue"),
        ("Read", "Read"),
        ("WebFetch", "WebFetch"),
    ],
)
def test_client_names_take_their_claude_code_shape(name, wire):
    assert claude_code_name(name) == wire


def test_declared_tools_are_sent_under_claude_code_names_and_restored():
    projected = _project(
        tools=[
            _function("exec_command"),
            _function("write_stdin"),
            {"type": "custom", "name": "apply_patch"},
            {"type": "namespace", "name": "collaboration", "tools": [_function("spawn_agent")]},
        ]
    )
    assert [tool["name"] for tool in projected.body["tools"]] == [
        "ExecCommand",
        "WriteStdin",
        "ApplyPatch",
        "CollaborationSpawnAgent",
    ]
    item = _called(projected, "CollaborationSpawnAgent")
    assert (item["type"], item.get("namespace"), item["name"]) == ("function_call", "collaboration", "spawn_agent")
    assert _called(projected, "ApplyPatch")["type"] == "custom_tool_call"


def test_colliding_names_are_numbered_in_declaration_order():
    projected = _project(tools=[_function("read"), _function("read_file"), _function("Read")])
    assert [tool["name"] for tool in projected.body["tools"]] == ["Read", "Read2", "Read3"]
    assert _called(projected, "Read2")["name"] == "read_file"
    assert _called(projected, "Read3")["name"] == "Read"


def test_names_beyond_the_wire_limit_are_shortened_with_a_stable_digest():
    long_name = "x" * 80
    names = ClaudeToolNames()
    wire = names.add(ToolIdentity(long_name, None, False))
    assert len(wire) == 64 and wire.startswith("X" + "x" * 52 + "_")
    assert ClaudeToolNames().add(ToolIdentity(long_name, None, False)) == wire
    assert names.resolve(wire) == ToolIdentity(long_name, None, False)


def test_unique_client_name_is_accepted_from_claude():
    projected = _project(tools=[_function("write_stdin")])
    assert _called(projected, "write_stdin")["name"] == "write_stdin"


def test_ambiguous_client_name_is_rejected():
    names = ClaudeToolNames()
    names.add(ToolIdentity("lookup", None, False))
    names.add(ToolIdentity("lookup", None, True))
    assert names.resolve("lookup") is None
    assert names.resolve("Lookup") == ToolIdentity("lookup", None, False)
    assert names.resolve("Lookup2") == ToolIdentity("lookup", None, True)


def test_undeclared_names_still_fail():
    projected = _project(tools=[_function("write_stdin")])
    with pytest.raises(ClaudeError, match="undeclared tool"):
        _called(projected, "exec_command")


def test_history_calls_replay_under_the_declared_wire_name():
    projected = _project(
        tools=[_function("exec_command")],
        input=[
            {"role": "user", "content": [{"type": "input_text", "text": "Run it"}]},
            {"type": "function_call", "call_id": "call_1", "name": "exec_command", "arguments": json.dumps({})},
            {"type": "function_call_output", "call_id": "call_1", "output": "ok"},
        ],
    )
    [tool_use] = [
        block
        for message in projected.body["messages"]
        for block in message["content"]
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]
    assert tool_use["name"] == "ExecCommand"


def test_forced_tool_choice_names_the_wire_tool():
    projected = _project(tools=[_function("exec_command")], tool_choice={"type": "function", "name": "exec_command"})
    assert projected.body["tool_choice"] == {"type": "tool", "name": "ExecCommand"}
