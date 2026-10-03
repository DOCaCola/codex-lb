## Why
Native checkpoint recovery state (readable snapshots, provenance, handoff
summaries and generation claims) is keyed by API key, client conversation ID and
checkpoint digest. A forked Codex thread gets a new conversation ID but replays
the identical encrypted checkpoint, so every lookup misses and switching the fork
to a source model fails with `compaction_history_unavailable`. Production hit this
on 2026-10-03 (conversation `01a102dd`, input index 219).

The conversation ID adds no protection: the same API key can send any
conversation ID, while the checkpoint digest addresses a ciphertext only that
key's client history contains. References agree: sub2api recovers encrypted
history by content identifier alone, and CLIProxyAPI derives session identity
from history content so forks inherit parent state.

## What Changes
- Address checkpoint recovery state by API key and checkpoint digest only.
- Forked conversations of the same key reuse the parent's readable snapshot,
  provenance and handoff summary; concurrent generation is deduplicated per
  key and checkpoint.
- Current access checks (key identity, account scope, model access) still gate
  every reuse.
- Records stored under the previous conversation-scoped keys are not migrated;
  they expire within their existing retention. A fork of a checkpoint minted
  before deployment fails once until its thread compacts again.

## Capabilities
### Modified Capabilities
- `model-source-routing`: content-addressed checkpoint recovery scope.

## Impact
Checkpoint recovery stores and their callers (HTTP, WebSocket, compact endpoint,
source continuation). No schema migration, client change or new setting.
