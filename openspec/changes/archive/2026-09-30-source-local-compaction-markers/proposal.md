# Proposal

## Why

Source dispatch currently rejects payload-free local context_compaction markers
as if they contained unreadable provider history. This blocks model switches
even when the surrounding summary is already plain text, and current logs do
not distinguish marker-only requests from genuine opaque checkpoints.

## What Changes

- Project recognized payload-free local markers out of source wire input while
  preserving summaries, ordinary history and retained logical input.
- Keep native OpenAI input unchanged and reject opaque, malformed and corrupt
  checkpoints before source dispatch with an indexed error.
- Log only request identity, compaction subtype, ciphertext presence and a bounded
  reason on rejection; aggregate successful marker omissions without content.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-source-routing`: classify local compaction markers separately from
  opaque checkpoints across source inference, replay and compaction.

## Impact

Shared compaction projection and unit/HTTP/WebSocket regression coverage.
No schema, setting, credentials, live-history edits or client fork.
