"""Claude Code-shaped wire names for translated client tools.

Anthropic fingerprints third-party agent harnesses on the OAuth Messages API by
their tool names: specific names, or a large set of recognizable snake_case
agent tools, are refused as "out of extra usage" (OmniRoute PR #2943). Opaque
names avoid that but read as noise to the model, which then calls the names its
instructions mention instead (CLIProxyAPI #6208). Following OmniRoute, client
tools are therefore sent under the Claude Code canonical name when one exists
and as PascalCase otherwise; namespaced tools are qualified as CLIProxyAPI does.
A request-local table restores the client's identity on the way back.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from app.modules.claude.tool_schema import ToolArguments

# OmniRoute open-sse/services/claudeCodeToolRemapper.ts TOOL_RENAME_MAP and
# claudeCodeExtraRemap.ts EXTRA_TOOL_RENAME_MAP.
_CLAUDE_CODE_NAMES: dict[str, str] = {
    "subagents": "SubDispatch",
    "session_status": "CheckStatus",
    "bash": "Bash",
    "read": "Read",
    "write": "Write",
    "edit": "Edit",
    "glob": "Glob",
    "grep": "Grep",
    "task": "Task",
    "agent": "Agent",
    "webfetch": "WebFetch",
    "websearch": "WebSearch",
    "todowrite": "TodoWrite",
    "todoread": "TodoRead",
    "question": "Question",
    "askuserquestion": "AskUserQuestion",
    "skill": "Skill",
    "slashcommand": "SlashCommand",
    "multiedit": "MultiEdit",
    "notebook": "Notebook",
    "notebookedit": "NotebookEdit",
    "notebookread": "NotebookRead",
    "lsp": "Lsp",
    "apply_patch": "ApplyPatch",
    "applypatch": "ApplyPatch",
    "bashoutput": "BashOutput",
    "killshell": "KillShell",
    "killbash": "KillBash",
    "enterplanmode": "EnterPlanMode",
    "exitplanmode": "ExitPlanMode",
    "enterworktree": "EnterWorktree",
    "exitworktree": "ExitWorktree",
    "artifact": "Artifact",
    "designsync": "DesignSync",
    "monitor": "Monitor",
    "sendmessage": "SendMessage",
    "listagents": "ListAgents",
    "pushnotification": "PushNotification",
    "reportfindings": "ReportFindings",
    "schedulewakeup": "ScheduleWakeup",
    "croncreate": "CronCreate",
    "crondelete": "CronDelete",
    "cronlist": "CronList",
    "taskoutput": "TaskOutput",
    "taskstop": "TaskStop",
    "taskcreate": "TaskCreate",
    "taskupdate": "TaskUpdate",
    "tasklist": "TaskList",
    "taskget": "TaskGet",
    "workflow": "Workflow",
}
# OmniRoute HARNESS_CANONICAL_MAP: common agent-harness tools with a Claude Code equivalent.
_HARNESS_NAMES: dict[str, str] = {
    "read_file": "Read",
    "write_file": "Write",
    "search_files": "Grep",
    "grep_search": "Grep",
    "list_directory": "Glob",
    "run_command": "Bash",
    "terminal": "Bash",
    "todo": "TodoWrite",
    "todo_write": "TodoWrite",
    "todo_read": "TodoRead",
    "patch": "Edit",
    "multi_edit": "MultiEdit",
}
_CLAUDE_CODE_TOOLS = frozenset(_CLAUDE_CODE_NAMES.values())
_WORD_SEPARATORS = re.compile(r"[_\s-]+")
_UNSAFE_CHARACTERS = re.compile(r"[^A-Za-z0-9_-]")
_MAX_NAME = 64
_WIRE_NAME = re.compile(rf"[A-Za-z0-9_-]{{1,{_MAX_NAME}}}\Z")


@dataclass(frozen=True)
class ToolIdentity:
    name: str
    namespace: str | None
    custom: bool
    arguments: ToolArguments | None = None
    # The client asked the OpenAI backend to encrypt some arguments; Claude returns them as plaintext.
    encrypted_arguments: bool = False
    # The client's own tool search (Responses ``tool_search``), not a function of that name.
    search: bool = False

    @property
    def key(self) -> tuple[str | None, str, bool, bool]:
        return (self.namespace, self.name, self.custom, self.search)

    @property
    def qualified_name(self) -> str:
        """The flat name a model would use for this tool (CLIProxyAPI qualifyResponsesNamespaceToolName)."""
        name, namespace = self.name, self.namespace
        if not namespace or name.startswith("mcp__") or name == namespace or name.startswith(namespace + "__"):
            return name
        return namespace + name if namespace.endswith("__") else f"{namespace}__{name}"


def claude_code_name(name: str) -> str:
    """The Claude Code-shaped form of a flat client tool name."""
    if name in _CLAUDE_CODE_TOOLS or name.startswith("mcp__"):
        return name
    if not (name[0].islower() or "_" in name or "-" in name):
        return name
    canonical = _CLAUDE_CODE_NAMES.get(name) or _HARNESS_NAMES.get(name)
    if canonical is not None:
        return canonical
    return "".join(part[0].upper() + part[1:] for part in _WORD_SEPARATORS.split(name) if part) or name


def _fit(name: str, seed: str) -> str:
    if _WIRE_NAME.fullmatch(name):
        return name
    digest = hashlib.sha256(seed.encode("utf-8", errors="surrogatepass")).hexdigest()[:10]
    return _UNSAFE_CHARACTERS.sub("_", name)[: _MAX_NAME - 11] + "_" + digest


@dataclass
class ClaudeToolNames:
    """One request's client tool identities, keyed by the name sent to Claude."""

    by_wire: dict[str, ToolIdentity] = field(default_factory=dict)
    _wire_by_key: dict[tuple[str | None, str, bool, bool], str] = field(default_factory=dict)
    _by_original: dict[str, ToolIdentity | None] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.by_wire)

    def __contains__(self, identity: ToolIdentity) -> bool:
        return identity.key in self._wire_by_key

    def identity(self, identity: ToolIdentity) -> ToolIdentity:
        """The registered identity with the same key, registering this one if new."""
        wire = self._wire_by_key.get(identity.key)
        return self.by_wire[wire] if wire is not None else self.by_wire[self.add(identity)]

    def wire_name(self, identity: ToolIdentity) -> str:
        return self._wire_by_key[identity.key]

    def add(self, identity: ToolIdentity) -> str:
        """Register a new identity; collisions are numbered in registration order, as OmniRoute does."""
        qualified = identity.qualified_name
        base = _fit(claude_code_name(qualified), qualified)
        wire, number = base, 2
        while wire in self.by_wire:
            suffix = str(number)
            wire = base[: _MAX_NAME - len(suffix)] + suffix
            number += 1
        self.by_wire[wire] = identity
        self._wire_by_key[identity.key] = wire
        # The original name is accepted on the way back only while it identifies one tool.
        self._by_original[qualified] = None if qualified in self._by_original else identity
        return wire

    def resolve(self, name: str) -> ToolIdentity | None:
        """The tool Claude called: its wire name, or the client's own name for exactly one tool.

        Instructions name tools by their client names, so Claude occasionally calls one directly.
        """
        return self.by_wire.get(name) or self._by_original.get(name)
