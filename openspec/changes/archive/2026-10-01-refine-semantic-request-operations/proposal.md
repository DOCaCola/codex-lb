# Proposal

## Why

Path-only attribution hides compactions dispatched through Responses and mislabels auxiliary checkpoint handoffs. Existing routing validation already identifies these operations without new payload inspection.

## What Changes

- Refine Responses operations from validated terminal compaction markers.
- Snapshot classification per websocket turn and preserve it across retries and forwarding.
- Label internal compact pings and scoped auxiliary checkpoint handoffs accurately.
- Add a localized checkpoint-handoff label in the existing Model-cell line.
- Preserve accounting, routing, privacy and historical records.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `provider-request-log-attribution`: semantic operation refinement from existing validation and isolation of nested/per-turn operations.

## Impact

Proxy ingress, websocket state, compact logging, automation logging, checkpoint resolution, operation enum and dashboard labels. No migration, new setting, deployment or history backfill.
