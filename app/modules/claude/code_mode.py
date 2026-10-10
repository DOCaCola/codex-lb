"""Codex code mode on translated Claude requests.

Codex advertises ``tool_mode: code_mode_only`` for Claude catalog rows, so its
tools arrive as one freeform ``exec`` whose input is JavaScript calling nested
helpers. GPT models are trained on that contract; Claude is not, and without
guidance it drops results it never passed to ``text()``, sends ``apply_patch``
an object, decorates patch markers, reaches for ``require`` or sleeps in a
shell. The contract below states those rules once per request (opencodex
``tool-catalog-nudge.ts`` / ``exec-tool-result-normalize.ts``). It names no
other tool, so it stays byte-identical while the tool set changes.
"""

from __future__ import annotations

from app.modules.claude.tool_names import ClaudeToolNames, ToolIdentity

# Codex's freeform JavaScript ``exec`` (codex-rs code-mode-protocol PUBLIC_TOOL_NAME).
CODE_MODE_EXEC = ToolIdentity("exec", None, True)
# Bare shell tools mean the flat tool surface, where an ``exec`` is not code mode.
_SHELL_BRIDGES = (ToolIdentity("exec_command", None, False), ToolIdentity("shell_command", None, False))


def code_mode_contract(tools: ClaudeToolNames) -> str | None:
    """The code-mode contract for a request that declares Codex code mode, else ``None``."""
    if CODE_MODE_EXEC not in tools or any(bridge in tools for bridge in _SHELL_BRIDGES):
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
