## Why
Under Codex code mode the only declared tool is the freeform `exec`; every other Codex tool is a nested helper called as `tools.<name>(...)` inside it. Claude sometimes calls such a helper directly. Since code mode went live, Haiku 5.5 calling `exec_command` failed its turn with `claude_undeclared_tool`. Freeform calls also arrive in shapes the adapter misreads: a body under `code` or `cmd` instead of `input` currently becomes a silently empty `exec` call.

opencodex, which hit the same failures across many routed models, compiles a nested helper call into the `exec` program that calls it (#2663, #3246, #5495, #5925). It also reads a freeform body through one alternate field or an outer Markdown fence (#4983), retargets a body that is exactly one patch to `tools.apply_patch` (#3498), and restores decorated patch delimiters.

## What Changes
- Under a code-mode catalog, an undeclared call to `exec_command`, `shell_command`, `write_stdin`, `apply_patch`, `view_image`, `create_goal`, `get_goal`, `update_goal` or a direct `mcp__<server>__<tool>` becomes an `exec` call whose program calls that helper. Arguments are serialized as data.
- Bare freeform `exec` and `apply_patch` bodies are read through `input`, or exactly one known alternate field, and an outer Markdown fence. A body with no faithful reading reaches the tool as the JSON Claude wrote, so the tool reports the error to the model.
- A code-mode `exec` body that is exactly one complete patch calls `tools.apply_patch`; JavaScript that merely contains a patch is unchanged. Decorated outer patch delimiters are restored.
- Each repaired call logs its kinds without content. A shell-shaped `exec` body is recorded but not rewritten; opencodex's repair for it (#5352) was observed only with StepFun.

## Capabilities
### Modified Capabilities
- `claude-accounts`: code-mode helper recovery and freeform tool input repair.

## Impact
Changes only Claude responses translated for Responses clients. Native Claude Code traffic and OpenAI models are unchanged. There is no schema or setting change.
