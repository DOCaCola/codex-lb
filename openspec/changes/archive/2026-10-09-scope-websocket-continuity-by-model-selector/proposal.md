## Why

Direct Responses WebSocket continuity currently remembers only the previous
response id and input prefix. When a client sends a full replay after changing
models, codex-lb can inject the prior model's response id, trim the replay to a
delta, and then route the new model through the prior subscription account. A
source-owned model is consequently sent to the ChatGPT backend and rejected as
unsupported even though the client supplied enough context for a fresh route.

## What Changes

- Bind proxy-injected direct-WebSocket continuity anchors to the exact effective
  model selector that produced the completed response.
- Inject and trim against an implicit session anchor only when the next turn has
  the same effective model selector.
- Preserve a model-switched full replay without a proxy-created
  `previous_response_id`, allowing the existing source-owned model guard to
  trigger its HTTP fallback before any subscription upstream send.
- Preserve the existing owner-evidence rules for a `previous_response_id` that
  the client supplied explicitly.
- Add direct-WebSocket regression coverage for native-to-source model switches
  with Codex session affinity enabled.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Scope implicit direct-WebSocket continuation anchors
  to the model selector that established them.

## Impact

Affected areas are the in-memory direct-WebSocket continuity record, session
anchor injection, model-source WebSocket fallback, and focused compatibility
tests. No database migration, setting, or public request/response schema change
is required.
