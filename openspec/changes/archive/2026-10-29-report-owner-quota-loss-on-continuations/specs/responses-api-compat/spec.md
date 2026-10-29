## ADDED Requirements

### Requirement: Spent continuation owners report their usage limit

When a Responses request is bound to its owner account only by the client's
own `previous_response_id`, and that owner cannot serve it because its
persisted status shows a spent upstream usage limit (`rate_limited` or
`quota_exceeded`), the service MUST fail the request with a message naming
the spent limit, its known reset time in UTC, and the instruction to retry
without `previous_response_id`. This applies when connect-time selection
cannot return the owner, when the owner refuses the anchored turn at
dispatch, and when a direct HTTP stream fails closed for an unselectable
owner.

On the Codex-native `/backend-api/codex/responses` WebSocket route the
failure MUST carry `error.code = "previous_response_not_found"`. An
unmodified Codex client answers that code with a full-history resend, which
ordinary selection serves on another account. Public routes and HTTP streams
MUST keep their existing owner-unavailable codes
(`previous_response_owner_unavailable`, or `upstream_unavailable` for a
dispatch refusal) and MUST NOT expose `previous_response_not_found`.
Continuity fail-closed telemetry MUST record reason `owner_quota_exhausted`.

A proxy-injected anchor, an input-file pin or a turn-state owner still binds
a resend without the client's anchor to the same account. Those requests,
owners lost for other reasons (authentication, deactivation, operator pause,
local capacity), and failed status lookups MUST keep the generic
owner-unavailable failure. A model admission limit keeps its own code and
message. Owner-only exhaustion MUST NOT be reported as pool-wide
`usage_limit_reached`.

#### Scenario: Codex client is told to leave a spent owner

- **GIVEN** a Codex-native WebSocket turn anchored by the client to a previous response
- **AND** the owner's persisted status is `rate_limited` with a known reset
- **WHEN** connect-time selection cannot return the owner
- **THEN** the client receives `previous_response_not_found` with a message naming the usage limit, the reset time, and retrying without `previous_response_id`
- **AND** the stale-anchor sanitizer does not replace that message

#### Scenario: Owner refuses an anchored turn at dispatch

- **GIVEN** a Codex-native WebSocket turn anchored by the client
- **WHEN** the owner refuses it with `usage_limit_reached` and its status is updated to a spent limit
- **THEN** the `response.failed` event carries `previous_response_not_found` with the usage-limit message

#### Scenario: Public routes keep their codes

- **GIVEN** a `/v1/responses` WebSocket or HTTP stream turn anchored to a spent owner
- **WHEN** the turn fails closed for that owner
- **THEN** it carries `previous_response_owner_unavailable` with the usage-limit message

#### Scenario: Bindings the client cannot drop stay generic

- **GIVEN** a turn whose anchor was injected by the proxy, or that is pinned by an input file or a turn-state owner
- **WHEN** its spent owner cannot be selected
- **THEN** the generic "Previous response owner account is unavailable; retry later." failure is returned
