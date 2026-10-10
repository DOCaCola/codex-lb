## Why
Codex runs its own models in code mode: a single JavaScript `exec` tool calls the other tools as nested helpers, so dependent calls and output filtering happen in one step. It also sends those models a base prompt written for code mode. Claude models receive the same prompt but are offered the flat tool list, so the instructions describe tools they don't have. Two things are missing for Claude to use code mode reliably:

- Codex's `notify()` adds extra outputs to an `exec` call after its result, and the Claude adapter currently rejects them as duplicate results.
- Claude isn't trained on the code-mode contract. Without guidance it forgets `text()`, so outputs come back empty; passes `apply_patch` an object; decorates patch markers; or reaches for `require`. opencodex adds a contract paragraph for these failures.

## What Changes
- The model catalog advertises `tool_mode: code_mode_only` for Claude models.
- When a translated request declares Codex's freeform `exec` and no bare `exec_command` or `shell_command`, the adapter appends a fixed code-mode contract to the system prompt, after the client's instructions. The contract names no other tools, so it doesn't change when the tool set changes.
- A later `custom_tool_call_output` for an answered code-mode `exec` call is a notification:
  - While that call's result is still in the open result turn, the notification is added to the same `tool_result`.
  - After a later assistant step, it becomes labelled user context after the newest results.
  - All other repeated results still fail.

## Capabilities
### Modified Capabilities
- `claude-accounts`: Claude models use Codex code mode, with its contract and `exec` notifications.

## Impact
Changes the model catalog and the Claude Responses→Messages projection. Codex clients switch Claude models to code mode after they refresh the catalog. Native Messages traffic and OpenAI models are unchanged. There is no schema change.
