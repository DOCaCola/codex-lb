## Why
Claude pool dispatch returns local busy when a selected account is full even if another authorized account has capacity.

## What Changes
- Reselect portable requests after atomic admission rejection, before any upstream send.
- Preserve hard ownership and same-account recovery constraints.
- Expose nullable per-worker concurrency in Claude account settings; default unlimited.

## Capabilities
### Modified Capabilities
- `claude-accounts`: admission-aware selection and concurrency settings.

## Impact
Claude settings, shared dispatch and dashboard; existing source concurrency column, no migration.
