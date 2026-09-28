# Native Claude resource provenance

## Why
Session affinity expires after one hour and cannot identify resources across a
soft account rebind. Preserve actual resource origins independently of affinity.

## What Changes
- Persist scoped server-tool identifiers before native output delivery.
- Resolve replay from resource origins with 30-day sliding retention.
- Reject unknown, expired and conflicting origins without guessing or backfill.
- Preserve translated replay and existing authorization/retry contracts.

## Capabilities
### Modified Capabilities
- `claude-accounts`: native resource provenance and delivery ordering.

## Impact
Claude dispatch/transport, a new SQL table/migration and regression tests.
