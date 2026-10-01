# Proposal

## Why

A known Claude quota block on an account-bound continuation currently returns 503, causing clients to treat exhaustion as a reconnectable server failure. The error should report the actual quota restriction without relaxing signed-history ownership.

## What Changes

- Return 429 for quota-only owner exclusions, retaining the owner-unavailable code and account scope.
- Describe observed blocking windows and include known reset/retry timing in HTTP and WebSocket errors.
- Preserve 503 for non-quota owner unavailability and preserve existing upstream-refusal settlement and retry rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: Accurate account-bound quota refusal and transport-independent retry diagnostics.

## Impact

Claude selection/error serialization, native Messages and translated Responses error boundaries, and regression coverage. No migrations, client changes, configuration changes or deployment.
