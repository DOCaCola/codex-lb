## Why
Claude upstream quota refusals currently strand requests even when another authorized account is available.

## What Changes
- Classify 429 scope before applying durable cooldowns.
- Reprepare eligible alternative accounts before output, within a shared four-send budget.
- Preserve strict history ownership, cancellation and per-attempt settlement.

## Capabilities
### Modified Capabilities
- `claude-accounts`: reactive quota failover.

## Impact
Claude routing/transport, shared source dispatch, a Claude cooldown table and regression tests. No automatic model or fast-mode downgrade.
