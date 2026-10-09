## Why
Claude OAuth accounts cannot discover or manually redeem available usage-reset grants. Safe redemption needs durable uncertain-outcome tracking and selective quota reconciliation.

## What Changes
- Add typed cedar_ember grant discovery and explicit confirmed redemption.
- Persist operation intent/results with identity binding, leases and same-ID retries.
- Preserve cleared-window provenance and reject stale pre-reset evidence.
- Reuse existing account controls/dialog styling; no automatic spending.

## Capabilities
### Modified Capabilities
- `claude-accounts`: manual reset grants and selective reconciliation.

## Impact
Claude client, account API/UI, SQL migrations, quota observation/refusal state and tests.
