# Proposal

## Why

Two limits remained after `claude-compaction-turn-boundary`.

1. Claude compaction refused completed signed Claude history unless its original
   account and model served the summary. Compacting after a Claude model switch
   (for example Sonnet 5 to Opus 5.5), or while the original account is paused,
   returned an error, and a historical signature rejection could not be recovered.
   A normal turn on the same history succeeds.
2. Manual-budget thinking models (Haiku 4.5, Sonnet 4.5) require the open
   assistant turn of a thinking-enabled request to begin with a thinking block.
   An open tool loop produced without signed Claude thinking (Sol tool calls with
   plaintext reasoning, an adaptive Claude turn that skipped thinking, or an effort
   change mid-loop) is rejected upstream with "Expected `thinking` or
   `redacted_thinking`, but found `tool_use`".

## What Changes

- Claude compaction authenticates signed history as before and prefers its
  original account. Completed signed thinking that cannot be replayed with its
  signature on the selected route becomes readable historical assistant text.
  Completed redacted thinking, which has no readable content, produces no block.
- Compaction signature recovery converts historical thinking to text instead of
  being skipped. Normal turns and native Messages keep the existing omission.
- Active-turn signed state and hosted search state remain bound to their original
  account and model in every mode; the shared client-history turn boundary decides
  what is active, including for compaction.
- A translated budget-thinking request whose open tool-use turn does not begin
  with signed thinking is sent with `thinking: {"type":"disabled"}` for that
  request only, with a content-free diagnostic. Adaptive models are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-source-routing`: source compaction history safety.
- `claude-accounts`: historical signature recovery, completed reasoning recovery,
  translated budget thinking in open tool turns.

## Impact

`app/modules/claude/replay.py`, `recovery.py`, `transport.py`, `protocol.py`;
unit and HTTP/WebSocket integration coverage. No API, schema, migration, client
or production configuration change.
