"""Claude calls to freeform tools and to nested code-mode helpers, read back as client input."""

import json
import logging

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import TokenEncryptor
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import project_responses
from app.modules.claude.responses import ResponsesProjection
from tests.claude_json_helpers import at

pytestmark = pytest.mark.unit

MODEL = "anthropic/claude-opus-5"
EXEC = {"type": "custom", "name": "exec", "description": "Run JavaScript"}
APPLY_PATCH = {"type": "custom", "name": "apply_patch", "description": "Apply a patch"}
WAIT = {"type": "function", "name": "wait", "parameters": {"type": "object", "properties": {}}}
SHELL = {"type": "function", "name": "exec_command", "parameters": {"type": "object", "properties": {}}}
MCP_EXEC = {"type": "namespace", "name": "mcp__runner", "tools": [EXEC]}
PATCH = "*** Begin Patch\n*** Update File: a.py\n@@\n-a\n+b\n*** End Patch"


def projection(tools):
    payload = {"model": MODEL, "input": "Hello", "tools": tools}
    projected = project_responses(payload, max_output_tokens=8192, reasoning=reasoning_spec(MODEL, None))
    opaque = ClaudeOpaqueState(TokenEncryptor(key=Fernet.generate_key()))
    return ResponsesProjection(OpaqueScope("source-a", MODEL, "key-a"), projected.tools, opaque)


def call(tools, name, arguments):
    response = projection(tools).complete(
        {
            "id": "msg1",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "content": [{"type": "tool_use", "id": "call1", "name": name, "input": arguments}],
        }
    )
    item = at(response, "output", 0)
    assert isinstance(item, dict)
    return item


def program(target, arguments):
    return f"const result = await {target}({json.dumps(arguments, separators=(',', ':'))});\ntext(result);"


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        (
            "exec_command",
            {"cmd": 'echo "x");process.exit()//', "workdir": "/repo"},
            program("tools.exec_command", {"cmd": 'echo "x");process.exit()//', "workdir": "/repo"}),
        ),
        ("shell_command", {"command": "ls"}, program("tools.exec_command", {"cmd": "ls"})),
        ("write_stdin", {"session_id": 3, "chars": ""}, program("tools.write_stdin", {"session_id": 3, "chars": ""})),
        ("update_goal", {"status": "complete"}, program("tools.update_goal", {"status": "complete"})),
        ("get_goal", {}, program("tools.get_goal", {})),
        (
            "view_image",
            {"file_path": "/a.png", "detail": "high"},
            'const result = await tools.view_image({"detail":"high","path":"/a.png"});\n'
            "if (result && result.image_url) { image(result.image_url); } else { text(result); }",
        ),
        ("apply_patch", {"input": PATCH}, program("tools.apply_patch", PATCH)),
        ("mcp__docs__search", {"q": "x"}, program("tools.mcp__docs__search", {"q": "x"})),
        ("mcp__my-docs__search", {}, program('tools["mcp__my-docs__search"]', {})),
    ],
)
def test_code_mode_helper_called_by_name_becomes_the_exec_program(caplog, name, arguments, expected):
    caplog.set_level(logging.INFO, logger="app.modules.claude.responses")
    item = call([EXEC, WAIT], name, arguments)
    assert (item["type"], item["name"], item["input"]) == ("custom_tool_call", "exec", expected)
    assert "claude_tool_input_repair source_id=source-a" in caplog.text
    assert "repairs=helper_name" in caplog.text
    assert "claude_undeclared_tool" not in caplog.text


def test_helper_patch_body_is_unwrapped_and_its_delimiters_restored(caplog):
    caplog.set_level(logging.INFO, logger="app.modules.claude.responses")
    decorated = PATCH.replace("Patch\n", "Patch ***\n", 1) + " ***"
    item = call([EXEC], "apply_patch", {"patch": f"```diff\n{decorated}\n```"})
    assert item["input"] == program("tools.apply_patch", PATCH)
    assert "recovered_from=apply_patch repairs=helper_name,field_patch,markdown_fence,patch_delimiters" in caplog.text
    assert "Update File" not in caplog.text


@pytest.mark.parametrize(
    ("tools", "name"),
    [
        ([EXEC, SHELL], "write_stdin"),
        ([{**SHELL, "name": "shell_command"}, EXEC], "apply_patch"),
        ([WAIT], "exec_command"),
        ([MCP_EXEC], "exec_command"),
        ([EXEC], "run_shell"),
        ([EXEC], "mcp__docs"),
        ([EXEC], "mcp____search"),
        ([EXEC], "mcp__docs__"),
    ],
)
def test_helper_names_outside_code_mode_remain_undeclared(tools, name):
    with pytest.raises(ClaudeError, match="undeclared tool"):
        call(tools, name, {"cmd": "ls"})


@pytest.mark.parametrize(
    ("arguments", "expected", "repairs"),
    [
        ({"code": "text(1)"}, "text(1)", "field_code"),
        ({"javascript": "text(1)", "note": "inspect"}, "text(1)", "field_javascript"),
        ({"input": "```js\ntext(1)\n```\n"}, "text(1)", "markdown_fence"),
        ({"script": "```\ntext(1)\n```"}, "text(1)", "field_script,markdown_fence"),
        ({"code": "a()", "script": "b()"}, '{"code":"a()","script":"b()"}', "unreadable_body"),
        ({"input": 5}, '{"input":5}', "unreadable_body"),
        ({"input": PATCH + "\n"}, program("tools.apply_patch", PATCH + "\n"), "patch_envelope"),
        (
            {"input": PATCH.replace("End Patch", "End Patch ***")},
            program("tools.apply_patch", PATCH),
            "patch_envelope,patch_delimiters",
        ),
    ],
)
def test_code_mode_exec_body_is_read_faithfully(caplog, arguments, expected, repairs):
    caplog.set_level(logging.INFO, logger="app.modules.claude.responses")
    item = call([EXEC, WAIT], "Exec", arguments)
    assert (item["name"], item["input"]) == ("exec", expected)
    assert f"tool=exec recovered_from=None repairs={repairs} shell_shaped=False" in caplog.text


@pytest.mark.parametrize(
    "body",
    [
        "text(1)",
        f"const patch = `{PATCH}`;\ntext(await tools.apply_patch(patch));",
        "*** Begin Patch\n*** End Patch",
        f"{PATCH}\ntext(1)",
        "```js\ntext(1)\n``` trailing",
    ],
)
def test_exec_programs_pass_through_byte_identical(caplog, body):
    caplog.set_level(logging.INFO, logger="app.modules.claude.responses")
    assert call([EXEC, WAIT], "Exec", {"input": body})["input"] == body
    assert "claude_tool_input_repair" not in caplog.text


@pytest.mark.parametrize(
    ("arguments", "expected", "repairs"),
    [
        ({"cmd": "git status", "workdir": "/repo"}, "git status", "field_cmd"),
        (
            {"input": '{"command":"npm test","yield_time_ms":1000}'},
            '{"command":"npm test","yield_time_ms":1000}',
            "none",
        ),
    ],
)
def test_shell_shaped_exec_body_is_recorded_without_its_content(caplog, arguments, expected, repairs):
    caplog.set_level(logging.INFO, logger="app.modules.claude.responses")
    assert call([EXEC], "Exec", arguments)["input"] == expected
    assert f"repairs={repairs} shell_shaped=True" in caplog.text
    assert "git status" not in caplog.text and "npm test" not in caplog.text


@pytest.mark.parametrize(
    "arguments",
    [
        {"cmd": "ls", "code": "text(1)"},
        {"cmd": "ls", "command": "pwd"},
        {"cmd": "ls", "env": "x"},
        {"cmd": " "},
        {"input": '{"cmd":"ls"}', "workdir": "/repo"},
    ],
)
def test_other_exec_bodies_are_not_shell_shaped(caplog, arguments):
    caplog.set_level(logging.INFO, logger="app.modules.claude.responses")
    call([EXEC], "Exec", arguments)
    assert "shell_shaped=True" not in caplog.text


def test_declared_patch_tool_gets_its_body_and_delimiters_repaired():
    decorated = PATCH.replace("Begin Patch", "Begin Patch ***")
    item = call([APPLY_PATCH, SHELL], "ApplyPatch", {"patch": decorated})
    assert (item["name"], item["input"]) == ("apply_patch", PATCH)


def test_flat_catalog_exec_is_never_retargeted_to_a_patch():
    assert call([EXEC, SHELL], "Exec", {"input": PATCH})["input"] == PATCH


def test_namespaced_freeform_tool_owns_its_grammar():
    item = call([MCP_EXEC], "mcp__runner__exec", {"code": "```\nx\n```"})
    assert (item["namespace"], item["input"]) == ("mcp__runner", '{"code":"```\\nx\\n```"}')


def test_recovered_helper_replays_as_its_exec_program():
    tools = [EXEC, WAIT]
    item = call(tools, "exec_command", {"cmd": "ls"})
    history = [
        {"role": "user", "content": "Hello"},
        item,
        {"type": "custom_tool_call_output", "call_id": "call1", "output": "a.txt"},
    ]
    payload = {"model": MODEL, "input": history, "tools": tools}
    body = project_responses(payload, max_output_tokens=8192, reasoning=reasoning_spec(MODEL, None)).body
    tool_use = at(body, "messages", 1, "content", 0)
    assert tool_use == {
        "type": "tool_use",
        "id": "call1",
        "name": "Exec",
        "input": {"input": program("tools.exec_command", {"cmd": "ls"})},
    }
