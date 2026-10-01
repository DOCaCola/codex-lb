# Proposal

## Why

Request-log model labels give reasoning and routine service tiers the same visual
weight as the model. Standard-tier noise makes the table harder to scan.

## What Changes

- Keep readable catalog model names and native technical-ID hover titles.
- Render reasoning effort and non-default service tiers inline in shared muted grey,
  without parentheses; omit the default tier from that label.
- Retain explicit requested-versus-actual differences and detailed raw metadata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-architecture`: separate request-log model identity from secondary metadata.

## Impact

Frontend request-log presentation, tests and specs only. No backend, pricing,
filtering or routing changes.
