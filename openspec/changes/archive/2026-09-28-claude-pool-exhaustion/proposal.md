## Why
Claude pool selection discards cooldown diagnostics and the source WebSocket bridge loses retry headers.

## What Changes
- Classify authorized pool exhaustion and preserve meaningful deadlines.
- Deliver native/Responses errors and safe WS retry headers consistently.

## Capabilities
### Modified Capabilities
- `claude-accounts`: scoped pool exhaustion diagnostics.
- `model-source-routing`: safe WebSocket error metadata.

## Impact
Claude selection, proxy errors, source WebSocket bridge and tests. No migration or new setting.
