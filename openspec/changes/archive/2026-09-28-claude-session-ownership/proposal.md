# Why
Native Claude currently treats thinking as account-bound state and rejects valid
self-contained history after affinity expires. References support preserving
native thinking and recovering only after an explicit upstream rejection.

# What Changes
- Treat native thinking as portable for account selection, retaining resource restrictions.
- Use scoped session/parent affinity and explicit identity conflict checks.
- Retry exactly once on an eligible historical-thinking signature rejection.
- Keep translated Responses envelope integrity and ownership checks unchanged.
- Record routing and recovery reasons without prompt or credential logging.

## Capabilities
### Modified Capabilities
- claude-accounts: native affinity and bounded signature recovery.

## Impact
Claude routing, dispatch, stream/JSON forwarding and tests. No schema migration,
longer retention, production configuration, commit or deployment.
