# Portable Effort Markers And Claude Overflow Code

## Why

Codex `2f3fb111be` (#56163, 2026-10-22) enables reasoning effort overrides by default. After a mid-thread effort
change, Codex inserts a `configuration_update` item into history and sends it to models whose catalog entry has
`supports_reasoning_effort_updates`; it omits the item for every other model. Native GPT-6 compaction input therefore
carries the item, and the readable checkpoint projection rejects it as unsupported state. The readable snapshot is
then not retained, and a later switch to Claude or OpenRouter depends on the checkpoint's producing account instead.

Anthropic reports input overflow as `invalid_request_error` with a message beginning "prompt is too long" and no
code. Codex recovers from overflow only by the `context_length_exceeded` code (history trimming during compaction,
turn recovery). CLIProxyAPI `43f27e3a` (#6869) adds that code for Responses clients. Production has no occurrence in
30 days because of the Claude context cap; this closes the gap.

## What Changes

- The readable checkpoint projection omits `configuration_update` like other protocol control items. Native requests
  and retained logical input keep it.
- Translated Claude Responses errors for prompt overflow carry `code: context_length_exceeded`. Native Messages
  errors are unchanged.

## Capabilities

### Modified Capabilities

- `model-source-routing`: adds "Readable checkpoint snapshots omit reasoning configuration markers".
- `claude-accounts`: adds "Translated Claude prompt overflow carries the context length code".

## Impact

- `app/modules/proxy/checkpoint_history.py` (`readable_checkpoint_input`).
- `app/modules/claude/transport.py` (translated stream open errors).
