## ADDED Requirements

### Requirement: Proxy-injected WebSocket continuity is model-selector scoped

The service MUST bind an implicitly injected direct Responses WebSocket
`previous_response_id` to the exact effective model selector that produced the
completed response. The selector MUST use the source-routing value after API-key
model enforcement while preserving an exact raw alias when source routing would
use that alias. The service MUST inject and trim against that implicit anchor
only when the next request has the same selector. A different or unknown
selector MUST leave the next request unanchored and MUST preserve its complete
input replay.

This requirement applies only to continuity synthesized by codex-lb. A
client-supplied `previous_response_id` MUST retain the existing recorded-owner
semantics.

#### Scenario: Same selector reuses implicit WebSocket continuity

- **GIVEN** a completed direct WebSocket turn recorded a response id, input
  prefix, and effective model selector
- **WHEN** the same WebSocket session sends a complete replay with the same
  effective model selector and no `previous_response_id`
- **THEN** the proxy MAY inject the completed response id
- **AND** it MAY trim the proven input prefix before the subscription upstream
  send

#### Scenario: Model transition preserves the complete replay

- **GIVEN** a completed direct WebSocket turn recorded an implicit continuity
  anchor for one effective model selector
- **WHEN** the same session sends a complete replay for a different effective
  model selector without `previous_response_id`
- **THEN** the proxy MUST NOT inject the earlier response id
- **AND** it MUST preserve the complete replay for routing and forwarding

#### Scenario: Native-to-source transition falls back before upstream send

- **GIVEN** a native subscription turn completed on a direct Responses
  WebSocket
- **AND** the next unanchored full replay selects a configured Responses model
  source
- **WHEN** the proxy evaluates the next `response.create`
- **THEN** it MUST emit `model_source_requires_http_transport`
- **AND** it MUST NOT send the source-owned model to the existing subscription
  upstream

#### Scenario: Client-supplied previous response remains owner-bound

- **GIVEN** the client explicitly supplies `previous_response_id`
- **AND** recorded subscription ownership resolves that response to an account
- **WHEN** the requested model is also configured on a model source
- **THEN** the existing subscription-owner routing requirement remains
  authoritative
