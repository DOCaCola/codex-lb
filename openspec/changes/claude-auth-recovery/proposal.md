## Why
Unexpected upstream401 currently cannot recover an unexpired but rejected Claude access token. Recovery must not overwrite newer grants or replay ambiguous refresh exchanges.

## What Changes
- Capture token/generation snapshots and support generation-aware forced refresh.
- Attempt one same-account authentication recovery before eligible account failover.
- Fence repeated-rejection backoff to the rejected generation.

## Capabilities
### Modified Capabilities
- `claude-accounts`: unexpected authentication recovery.

## Impact
Claude auth, preparation and shared dispatch. No schema change or deployment configuration.
