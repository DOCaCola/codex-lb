## MODIFIED Requirements

### Requirement: Oversized response.create payloads are slimmed or rejected before upstream send

When the service prepares a Responses `response.create` request for the
upstream websocket, it MUST measure the serialized outbound request size before
sending it upstream. If the payload exceeds the upstream websocket budget, the
service MUST first attempt to slim only the historical portion of `input` that
precedes the most recent user turn: historical inline images MUST be replaced
with textual omission notices, and oversized historical tool outputs MUST be
replaced with textual omission notices that preserve the item in sequence.

If a client-facing WebSocket request still exceeds the budget after slimming,
the service MUST fail locally with status `413`, carrying
`error.code = "payload_too_large"`, `error.type = "invalid_request_error"`, and
`error.param = "input"`. This retryable HTTP-status error MUST give the Codex
client an opportunity to use its WebSocket-to-HTTPS fallback and obtain the
upstream HTTP endpoint's result.

If an HTTP request or another non-WebSocket request state still exceeds the
budget after slimming, the service MUST retain status `400` with the same error
envelope. Every local rejection MUST occur before an upstream WebSocket is
allocated or reused.

#### Scenario: Historical inline artifacts are slimmed and the latest user turn is preserved

- **WHEN** a Responses request exceeds the upstream websocket budget because historical inline images or historical oversized tool outputs dominate the serialized `input`
- **AND** replacing those historical artifacts with omission notices reduces the serialized request below budget
- **THEN** the service forwards the slimmed `response.create` upstream
- **AND** it preserves the most recent user turn unchanged

#### Scenario: HTTP Responses route retains a terminal status when the payload still exceeds budget

- **WHEN** an HTTP `/v1/responses` or `/backend-api/codex/responses` request still exceeds the upstream websocket budget after historical slimming
- **THEN** the service returns HTTP `400`
- **AND** the error envelope code is `payload_too_large`
- **AND** the error envelope type is `invalid_request_error`
- **AND** the error envelope param is `input`
- **AND** the service MUST NOT allocate or reuse an upstream websocket bridge session for that request

#### Scenario: Websocket Responses route exposes the Codex HTTP recovery path

- **WHEN** a websocket `/v1/responses` or `/backend-api/codex/responses` request still exceeds the upstream websocket budget after historical slimming
- **THEN** the service emits a websocket error event with `"type": "error"` and `"status": 413`
- **AND** the error envelope code is `payload_too_large`
- **AND** the error envelope type is `invalid_request_error`
- **AND** the error envelope param is `input`
- **AND** the service MUST NOT connect the upstream websocket for that request
