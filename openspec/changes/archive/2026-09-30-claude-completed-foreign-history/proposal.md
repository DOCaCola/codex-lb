# Proposal

## Why

Ordinary Sol-to-Claude switches remain blocked by historical encrypted reasoning
with empty summaries. Completed private provider state is not mandatory Claude
conversation context and must not prevent replay of the surrounding visible history.

## What Changes

- Exclude completed foreign opaque-only reasoning from Claude wire blocks while
  retaining the original encrypted item in logical history.
- Preserve readable reasoning as assistant text, all messages and tool pairs,
  item positions for diagnostics, and genuine Claude signed-state authentication.
- Record content-free conversion and omission counts. Active foreign state and
  complete-history compaction retain explicit refusal semantics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: completed opaque-only foreign reasoning is omitted only from
  outbound Claude inference instead of blocking otherwise portable conversation.

## Impact

Shared Claude Responses preparation, HTTP/WebSocket and retained replay tests,
and Claude account specifications. No credentials, schema, settings, live-history
edits, client changes or additional inference sends.
