# Proposal

## Why

Switching a conversation from Sol to Opus and then compacting fails before dispatch
with "Complete compaction contains encrypted state from another provider". Normal
Opus turns on the same history succeed. On 2026-10-01 (conversation 01a0eec6…),
an Opus turn at 14:20:59 projected 3 readable and 66 opaque-only foreign items
successfully. Auto compaction at 14:22:02 was then refused, and the user had to
switch back to Sol to compact.

## What Changes

- Claude source compaction accepts exactly the foreign reasoning a normal Claude
  turn on the same history accepts. Completed foreign reasoning becomes readable
  assistant text or produces no wire block.
- The appended summarization instruction no longer defines the turn boundary.
  The boundary is computed on the client-supplied history: a history ending with
  an assistant message is a closed turn; otherwise the last real user or external
  task input starts the active turn.
- Foreign ciphertext inside an open tool loop still fails with
  `nonportable_provider_history` and its input index, reported as an active
  continuation.
- The summarization instruction item has one shared builder, so the Claude
  preparer identifies it structurally.
- Unchanged: authentication, ownership and same-model rules for genuine Claude
  envelopes, checkpoint materialization and handoff, and untouched history after
  a failed compaction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: foreign reasoning at Claude dispatch, compaction boundary.

## Impact

`app/modules/model_sources/compaction.py`, `app/modules/claude/replay.py`, unit
and HTTP/WS integration coverage. No API, schema, migration, client or production
configuration change.
