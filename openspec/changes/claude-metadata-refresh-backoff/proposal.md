## Why
Claude metadata endpoints rate-limit independently of inference. Minute polling and concurrent manual refreshes amplify 429s and currently lose the retry hint.

## What Changes
Coordinate per-endpoint refreshes durably, poll usage every three minutes, honor Retry-After, preserve observations and expose endpoint-specific errors.

## Capabilities
### New Capabilities
### Modified Capabilities
- `claude-accounts`: coordinated metadata refresh and durable cooldown.

## Impact
Claude client/service/scheduler, account state JSON, tests and existing account diagnostics. No migration, new settings, or inference routing changes.
