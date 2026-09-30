# Proposal

## Why

Switching translated Claude history to native Codex forwards proxy-issued reasoning IDs and Claude envelopes that OpenAI cannot resolve or decrypt. Existing sanitation also discards plaintext reasoning instead of retaining its portable meaning.

## What Changes

- Authenticate Claude history before native projection using the original client/conversation scope.
- Preserve readable thinking as native reasoning summaries, leaving retained logical history and paired tools unchanged.
- Reject redacted thinking and Claude server-search state explicitly when their semantics cannot be represented at the new destination.
- Normalize item identities by type without fabricating provider identities; preserve valid native opaque reasoning.
- Cover HTTP, WebSocket, retained continuation and native compaction paths without client changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: authenticated projection of Claude history onto native Codex.

## Impact

Claude replay projection, native proxy request preparation and Responses sanitation. No schema migration, new settings, client changes or production deployment.
