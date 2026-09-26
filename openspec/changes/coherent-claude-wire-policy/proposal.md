## Why

Claude forwarding currently replaces session headers without aligning body metadata,
drops native helper/agent hints, and adds thinking/effort betas to native requests.
Reference failures show that mixed identities and unrequested beta activation are
not transparent forwarding.

## What Changes

- Project session metadata and headers from one account/conversation-bound snapshot.
- Preserve reviewed native software/request hints and native beta negotiation.
- Recognize count-token and structured helper traffic without requiring the main system identity.
- Define endpoint defaults and regression-test real route dispatch.

## Capabilities

### Modified Capabilities
- `claude-accounts`: coherent native and translated OAuth request policy.

## Impact

Claude request preparation and tests only; no migration, deployment, TLS change or new setting.
