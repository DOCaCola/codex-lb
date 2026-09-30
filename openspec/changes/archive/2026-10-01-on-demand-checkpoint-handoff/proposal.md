# Proposal

## Why

Native encrypted checkpoints make provider switches fail once readable recovery
expires. Producing summaries at every native compaction changes ordinary operation
unnecessarily; retaining whole conversations is not the desired solution.

## What Changes

- Retain lightweight, scope- and digest-bound native checkpoint provenance after
  successful settlement, including when the native input contains older opaque state.
- Generate a portable handoff only when a source needs an unreadable checkpoint,
  using its verified original model/account and normal metering and logging.
- Cache the generated summary, not the original conversation; serialize generation
  across workers and fail explicitly on missing provenance, owner loss or invalid output.
- Leave native wire behavior, readable histories and existing available recovery
  snapshots unchanged. Stop automatically capturing whole precompact conversations.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-source-routing`: on-demand native checkpoint handoff and bounded provenance.

## Impact

Native compact completion hooks, source history preparation, owner-pinned native
streaming, private checkpoint storage and HTTP/WS regression coverage. No client
fork, production changes or new primary database migration.
