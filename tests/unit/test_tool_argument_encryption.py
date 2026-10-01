import pytest

from app.core.openai.tool_argument_encryption import (
    declares_encrypted_arguments,
    mark_plaintext_arguments,
    tools_with_encrypted_arguments,
)

pytestmark = pytest.mark.unit

ENCRYPTED = {"type": "object", "properties": {"message": {"type": "string", "encrypted": True}}}
PLAIN = {"type": "object", "properties": {"path": {"type": "string"}}}


def test_declarations_follow_encrypted_parameters_and_namespaces():
    tools = [
        {
            "type": "namespace",
            "name": "collaboration",
            "tools": [
                {"type": "function", "name": "spawn_agent", "parameters": ENCRYPTED},
                {"type": "function", "name": "list_agents", "parameters": PLAIN},
            ],
        },
        {"type": "function", "name": "notify", "parameters": ENCRYPTED},
        {"type": "custom", "name": "exec"},
        {"type": "web_search"},
    ]
    assert tools_with_encrypted_arguments(tools) == {("collaboration", "spawn_agent"), (None, "notify")}
    assert not declares_encrypted_arguments({"type": "object", "properties": {"m": {"encrypted": "yes"}}})
    assert tools_with_encrypted_arguments(None) == frozenset()


def test_only_declared_function_calls_are_marked():
    declared = frozenset({("collaboration", "spawn_agent")})
    spawn = {"type": "function_call", "namespace": "collaboration", "name": "spawn_agent", "arguments": "{}"}
    unnamespaced = {"type": "function_call", "name": "spawn_agent", "arguments": "{}"}
    custom = {"type": "custom_tool_call", "namespace": "collaboration", "name": "spawn_agent", "input": ""}
    for item in (spawn, unnamespaced, custom):
        mark_plaintext_arguments(item, declared)
    assert spawn["encrypted_function_args"] == []
    assert "encrypted_function_args" not in unnamespaced
    assert "encrypted_function_args" not in custom
