"""Codex code mode projected onto Claude Messages."""

from copy import deepcopy

import pytest

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.protocol import project_responses

pytestmark = pytest.mark.unit

EXEC = {
    "type": "custom",
    "name": "exec",
    "description": "Run JavaScript code to orchestrate/compose tool calls",
    "format": {"type": "grammar", "syntax": "lark", "definition": "start: /.+/"},
}
WAIT = {"type": "function", "name": "wait", "parameters": {"type": "object", "properties": {}}}
SHELL = {"type": "function", "name": "exec_command", "parameters": {"type": "object", "properties": {}}}


def project(**payload):
    payload = {"model": "anthropic/claude-opus-5", "instructions": "Codex base instructions", **payload}
    original = deepcopy(payload)
    body = project_responses(payload, max_output_tokens=8192, reasoning=reasoning_spec(payload["model"], None)).body
    assert payload == original
    return body


def exec_call(call_id):
    return {"type": "custom_tool_call", "call_id": call_id, "name": "exec", "input": "text(1)"}


def exec_output(call_id, text):
    return {"type": "custom_tool_call_output", "call_id": call_id, "output": text}


def test_code_mode_contract_follows_the_client_instructions():
    system = project(tools=[EXEC, WAIT], input="Hello")["system"]
    assert system[0] == {"type": "text", "text": "Codex base instructions"}
    assert len(system) == 2
    contract = system[1]["text"]
    assert contract.startswith("Code mode: the `Exec` tool runs JavaScript")
    assert "text(...)" in contract and "*** Begin Patch" in contract and "ALL_TOOLS" in contract


def test_code_mode_contract_is_identical_across_tool_sets():
    other = {"type": "function", "name": "request_user_input", "parameters": {"type": "object", "properties": {}}}
    assert project(tools=[EXEC], input="Hello")["system"] == project(tools=[EXEC, WAIT, other], input="Hi")["system"]


@pytest.mark.parametrize(
    "tools",
    [
        [],
        [WAIT],
        [EXEC, SHELL],
        [{**SHELL, "name": "shell_command"}, EXEC],
        [{"type": "function", "name": "exec", "parameters": {"type": "object", "properties": {}}}],
        [{"type": "namespace", "name": "mcp__box", "tools": [EXEC]}],
    ],
)
def test_code_mode_contract_requires_codex_code_mode(tools):
    assert project(tools=tools, input="Hello")["system"] == [{"type": "text", "text": "Codex base instructions"}]


def test_namespaced_shell_tool_keeps_code_mode():
    shell = {"type": "namespace", "name": "mcp__docker", "tools": [SHELL]}
    assert len(project(tools=[EXEC, shell], input="Hello")["system"]) == 2


def test_notification_in_the_open_result_turn_extends_the_exec_result():
    messages = project(
        tools=[EXEC, WAIT],
        input=[
            {"role": "user", "content": "Run it"},
            exec_call("call-1"),
            exec_output("call-1", "final"),
            exec_output("call-1", "progress"),
        ],
    )["messages"]
    assert messages[-1] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call-1",
                "content": [{"type": "text", "text": "final"}, {"type": "text", "text": "progress"}],
            }
        ],
    }


def test_notification_after_a_wait_cycle_is_labelled_context_after_the_results():
    messages = project(
        tools=[EXEC, WAIT],
        input=[
            {"role": "user", "content": "Run it"},
            exec_call("call-1"),
            exec_output("call-1", "Script running with cell ID 1"),
            {"type": "function_call", "call_id": "call-2", "name": "wait", "arguments": '{"cell_id": "1"}'},
            {"type": "function_call_output", "call_id": "call-2", "output": "done"},
            exec_output("call-1", "progress"),
            {"role": "user", "content": "Thanks"},
        ],
    )["messages"]
    assert messages[-1]["content"] == [
        {"type": "tool_result", "tool_use_id": "call-2", "content": [{"type": "text", "text": "done"}]},
        {"type": "text", "text": "[Later exec output: tool_use_id=call-1]"},
        {"type": "text", "text": "progress"},
        {"type": "text", "text": "Thanks"},
    ]
    assert messages[2]["content"][0]["content"] == [{"type": "text", "text": "Script running with cell ID 1"}]


@pytest.mark.parametrize(
    "items",
    [
        # Only code-mode exec produces later outputs; other repeated results stay invalid.
        [
            {"type": "function_call", "call_id": "call-1", "name": "wait", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "call-1", "output": "a"},
            {"type": "function_call_output", "call_id": "call-1", "output": "b"},
        ],
        [
            {**exec_call("call-1"), "name": "apply_patch"},
            exec_output("call-1", "a"),
            exec_output("call-1", "b"),
        ],
        [
            exec_call("call-1"),
            exec_output("call-1", "a"),
            {**exec_output("call-1", "b"), "type": "function_call_output"},
        ],
        # A notification cannot interrupt an open tool cycle.
        [
            exec_call("call-1"),
            exec_output("call-1", "a"),
            {"type": "function_call", "call_id": "call-2", "name": "wait", "arguments": "{}"},
            exec_output("call-1", "b"),
        ],
    ],
)
def test_other_repeated_results_remain_invalid(items):
    with pytest.raises(ClientPayloadError, match="duplicate_result"):
        project(tools=[EXEC, WAIT], input=[{"role": "user", "content": "Run it"}, *items])
