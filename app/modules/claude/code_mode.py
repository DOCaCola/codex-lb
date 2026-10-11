"""Codex code mode on translated Claude requests.

Codex advertises ``tool_mode: code_mode_only`` for Claude catalog rows, so its
tools arrive as one freeform ``exec`` whose input is JavaScript calling nested
helpers. GPT models are trained on that contract; Claude is not, and without
guidance it drops results it never passed to ``text()``, sends ``apply_patch``
an object, decorates patch markers, reaches for ``require`` or sleeps in a
shell. The contract below states those rules once per request (opencodex
``tool-catalog-nudge.ts`` / ``exec-tool-result-normalize.ts``). It names no
other tool, so it stays byte-identical while the tool set changes.

Claude still sometimes calls a nested helper such as ``exec_command`` by its own
name, or sends a whole patch as the ``exec`` body. Under a code-mode catalog each
such call has exactly one meaning: the ``exec`` program that calls that helper.
It is compiled into that program, with arguments serialized as data, never as
source (opencodex ``code-mode-helper-compat.ts``, #2663, #3498, #5495, #5925).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import JsonValue

from app.modules.claude.freeform import (
    FreeformBody,
    freeform_body,
    freeform_grammar,
    is_patch_envelope,
    normalize_patch_delimiters,
)
from app.modules.claude.tool_names import ClaudeToolNames, ToolIdentity

# Codex's freeform JavaScript ``exec`` (codex-rs code-mode-protocol PUBLIC_TOOL_NAME).
CODE_MODE_EXEC = ToolIdentity("exec", None, True)
# Bare shell tools mean the flat tool surface, where an ``exec`` is not code mode.
_SHELL_BRIDGES = (ToolIdentity("exec_command", None, False), ToolIdentity("shell_command", None, False))
# Nested helpers code mode reaches only as ``tools.<name>(...)`` inside ``exec``
# (opencodex CODE_MODE_HELPER_TOOL_NAMES). Code mode has no ``shell_command``;
# its nested shell is ``exec_command``.
_HELPERS = frozenset(
    {
        "exec_command",
        "shell_command",
        "write_stdin",
        "apply_patch",
        "view_image",
        "create_goal",
        "get_goal",
        "update_goal",
    }
)
_JS_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
# Keys of Codex's ``exec_command`` arguments; an ``exec`` body made of only these is a shell call.
_SHELL_KEYS = frozenset(
    {
        "cmd",
        "command",
        "workdir",
        "shell",
        "login",
        "tty",
        "yield_time_ms",
        "max_output_tokens",
        "sandbox_permissions",
        "justification",
        "prefix_rule",
    }
)
_VIEW_IMAGE_PATH_ALIASES = ("file_path", "file", "image_path")


@dataclass(frozen=True)
class ToolInput(FreeformBody):
    # An ``exec`` body that is a JSON shell call (opencodex #5352). Recorded, not repaired:
    # no Claude model has been seen sending it, and its JavaScript reading fails visibly.
    shell_shaped: bool = False


def declares_code_mode(tools: ClaudeToolNames) -> bool:
    """Whether the request declares Codex code mode: a bare freeform ``exec`` and no bare shell tool."""
    return CODE_MODE_EXEC in tools and not any(bridge in tools for bridge in _SHELL_BRIDGES)


def code_mode_contract(tools: ClaudeToolNames) -> str | None:
    """The code-mode contract for a request that declares Codex code mode, else ``None``."""
    if not declares_code_mode(tools):
        return None
    exec_name = tools.wire_name(CODE_MODE_EXEC)
    return (
        f"Code mode: the `{exec_name}` tool runs JavaScript in an isolated V8 runtime, not a shell. "
        "Call the other Codex tools inside it as `await tools.<name>(...)`, for example "
        '`await tools.exec_command({cmd: "ls"})`. A helper missing from the top-level tool list or from '
        f"`{exec_name}`'s description is still callable on `tools`; find it in the global `ALL_TOOLS`. "
        "Nothing is echoed automatically: a final expression or an awaited result you do not print is "
        "discarded and the cell reports empty output. Pass everything you need to read to `text(...)` in "
        "the same cell, and treat empty output as a missing `text(...)` call, not as a failed command. "
        "`tools.apply_patch(patch)` takes exactly one string, never an object; the patch starts with the "
        "line `*** Begin Patch` and ends with the line `*** End Patch`, with no code fence, prose or extra "
        "asterisks on those lines. The runtime has no `import`, `require` or module loader; use the globals "
        f"`{exec_name}` describes. For a command that may outlive `yield_time_ms`, let `tools.exec_command` "
        'return a `session_id` and poll it later with `tools.write_stdin({session_id, chars: ""})` '
        "instead of sleeping."
    )


def _is_mcp_direct(name: str) -> bool:
    """A flattened ``mcp__<server>__<tool>`` name with both parts present."""
    if not name.startswith("mcp__"):
        return False
    rest = name[len("mcp__") :]
    separator = rest.find("__")
    return separator > 0 and separator + 2 < len(rest)


def code_mode_helper(tools: ClaudeToolNames, name: str) -> str | None:
    """The nested helper an undeclared call names under Codex code mode, else ``None``."""
    if declares_code_mode(tools) and (name in _HELPERS or _is_mcp_direct(name)):
        return name
    return None


def _data(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _call(target: str, payload: JsonValue) -> str:
    return f"const result = await {target}({_data(payload)});\ntext(result);"


def _apply_patch(body: FreeformBody, *labels: str) -> ToolInput:
    patch = normalize_patch_delimiters(body.text)
    return ToolInput(_call("tools.apply_patch", patch.text), (*labels, *body.repairs, *patch.repairs))


def _helper_input(helper: str, arguments: dict[str, JsonValue]) -> ToolInput:
    if helper == "apply_patch":
        return _apply_patch(freeform_body(arguments, "apply_patch"), "helper_name")
    args = dict(arguments)
    if helper == "shell_command" and isinstance(args.get("command"), str) and "cmd" not in args:
        args["cmd"] = args.pop("command")
    if helper == "view_image":
        for alias in _VIEW_IMAGE_PATH_ALIASES:
            value = args.pop(alias, None)
            if not isinstance(args.get("path"), str) and isinstance(value, str):
                args["path"] = value
        return ToolInput(
            f"const result = await tools.view_image({_data(args)});\n"
            "if (result && result.image_url) { image(result.image_url); } else { text(result); }",
            ("helper_name",),
        )
    if helper in ("exec_command", "shell_command"):
        target = "tools.exec_command"
    else:
        target = f"tools.{helper}" if _JS_IDENTIFIER.fullmatch(helper) else f"tools[{_data(helper)}]"
    return ToolInput(_call(target, args), ("helper_name",))


def _shell_shaped(arguments: dict[str, JsonValue]) -> bool:
    value: JsonValue = arguments
    if "input" in arguments:
        wrapped = arguments["input"]
        if len(arguments) != 1 or not isinstance(wrapped, str):
            return False
        try:
            value = json.loads(wrapped)
        except ValueError:
            return False
    if not isinstance(value, dict) or not value.keys() <= _SHELL_KEYS:
        return False
    commands = [value[key] for key in ("cmd", "command") if key in value]
    return len(commands) == 1 and isinstance(commands[0], str) and bool(commands[0].strip())


def custom_tool_input(
    tools: ClaudeToolNames, identity: ToolIdentity, arguments: dict[str, JsonValue], helper: str | None
) -> ToolInput:
    """The client input for a Claude call to a freeform tool, or to a helper it recovered as code-mode ``exec``."""
    if helper is not None:
        return _helper_input(helper, arguments)
    grammar = freeform_grammar(identity.name, identity.namespace)
    body = freeform_body(arguments, grammar)
    if grammar == "apply_patch":
        patch = normalize_patch_delimiters(body.text)
        return ToolInput(patch.text, (*body.repairs, *patch.repairs))
    if grammar != "exec" or not declares_code_mode(tools):
        return ToolInput(body.text, body.repairs)
    if is_patch_envelope(body.text):
        return _apply_patch(body, "patch_envelope")
    return ToolInput(body.text, body.repairs, shell_shaped=_shell_shaped(arguments))
