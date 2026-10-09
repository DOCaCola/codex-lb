## Why
Unified Claude 429 status can describe an overage/model rejection while shared subscription windows remain healthy. Treating it as account-wide blocks unrelated models.

## What Changes
- Classify shared and model-specific refusals independently, retaining scoped deadlines.
- Persist mixed restrictions atomically without extending shared cooldowns to model deadlines.
- Preserve existing failover, ownership, settlement and fast-mode entitlement behavior.

## Capabilities
### Modified Capabilities
- `claude-accounts`: scoped overage refusal handling.

## Impact
Claude refusal classifier, persistence and regression tests. No new settings, migration, spending policy or deployment.
