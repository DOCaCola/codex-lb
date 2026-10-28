## Why

Request-log plan tags currently collapse eleven named account tiers into four colors: Max tiers alias Pro, Enterprise aliases Team, and unmapped tiers inherit Free's gray. The approved HTML palette makes individual tiers recognizable in both dashboard themes.

## What Changes

- Apply the approved per-plan text, background, border, and hover colors through a shared plan badge.
- Preserve provider-specific labels and missing snapshots; give unknown values a neutral presentation distinct from Free.
- Include explicit colors for the six recognized rate-limit metadata keys without changing account plan eligibility.

## Capabilities

### Modified Capabilities
- `frontend-architecture`: distinct and readable plan tags in recent requests.

## Impact

Frontend presentation only. No API, database, account color, routing, or subscription normalization changes.
