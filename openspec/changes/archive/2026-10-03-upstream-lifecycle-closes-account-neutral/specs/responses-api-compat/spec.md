# responses-api-compat Delta

## MODIFIED Requirements

### Requirement: Upstream websocket drops penalize affected accounts

When an upstream websocket closes while one or more streamed response requests
are pending and have not reached a terminal event, the proxy MUST record a
transient upstream error for the account before signaling failure for those
pending requests, except when the close carries a classified process-wide
network failure or upstream WebSocket liveness timeout, is a received
server-lifecycle close frame (`close_code` 1000, 1001 or 1012, before or after
response events), or carries the classified per-socket
`upstream_keepalive_timeout` transport error. Server-lifecycle closes,
keepalive timeouts, process-wide network failures, and liveness timeouts MUST
remain account-neutral and use their classified error and bounded retry or
retry-circuit handling. For other closes, the proxy MUST surface
`stream_incomplete` to affected pending requests except when a direct Responses
WebSocket request has already successfully emitted a finite integer
`sequence_number`. For that sequenced direct-WebSocket case, the proxy MUST
record the request outcome as `stream_incomplete` without emitting a synthetic
terminal frame under the active response id, then MUST close the downstream
WebSocket with code 1011, unless the request satisfies the verified
no-generation prewarm recovery contract defined in "Direct WebSocket replay
never mixes numeric response sequences" and its one-shot replay succeeds.

#### Scenario: websocket closes before pending responses complete
- **GIVEN** a streamed response request is pending on an upstream websocket
- **AND** the direct downstream response has not emitted a numeric sequence, or the request uses another transport
- **WHEN** the websocket closes before a terminal response event is observed
- **AND** the close does not carry a classified process-wide network failure or upstream WebSocket liveness timeout
- **AND** the close is not a received server-lifecycle close frame
- **THEN** the pending request fails with `stream_incomplete`
- **AND** the account receives a transient upstream failure signal for routing

#### Scenario: sequenced direct websocket closes before completion
- **GIVEN** a direct Responses WebSocket request has successfully emitted a finite integer `sequence_number`
- **AND** the request does not satisfy the verified no-generation prewarm recovery contract
- **WHEN** the upstream websocket closes before a terminal response event is observed
- **AND** the close does not carry a classified process-wide network failure or upstream WebSocket liveness timeout
- **THEN** the request is recorded as failed with `stream_incomplete`
- **AND** no synthetic terminal frame is emitted under the active response id
- **AND** the downstream WebSocket closes with code 1011
- **AND** the account receives a transient upstream failure signal for routing unless the close is a received server-lifecycle close frame

#### Scenario: server-lifecycle close remains account neutral
- **GIVEN** a streamed response request is pending on an upstream websocket, on the direct Responses WebSocket or the HTTP bridge
- **WHEN** the upstream sends a close frame with code 1000, 1001 or 1012 before the terminal event, before or after response events
- **THEN** the pending request fails with `stream_incomplete` naming the close code
- **AND** the account receives no failure-health signal

#### Scenario: websocket liveness timeout remains account neutral
- **GIVEN** a streamed response request is pending on an upstream websocket
- **WHEN** its transport reports `upstream_websocket_liveness_timeout`
- **THEN** the pending request fails with that classified error code
- **AND** the account receives no failure-health signal
- **AND** the request is not transparently replayed

#### Scenario: clean pre-response close does not penalize the account
- **GIVEN** a hard-affinity HTTP bridge request is pending with no surfaced response event
- **WHEN** the upstream websocket closes cleanly before response output
- **THEN** the proxy records the clean-close retry-circuit outcome
- **AND** the selected account is not penalized

#### Scenario: created-only generate-false Codex prewarm recovers
- **GIVEN** a direct Responses WebSocket request is classified by Codex turn
  metadata as `request_kind = "prewarm"`
- **AND** its normalized request body contains `generate = false`
- **AND** only `response.created` at numeric sequence `0` has been sent
  downstream, with no other response progress or visible output
- **WHEN** the upstream websocket closes before the terminal event
- **THEN** the proxy MAY perform the existing bounded one-shot replay
- **AND** it suppresses the replayed `response.created`
- **AND** it forwards only replay numeric sequences that advance beyond `0`
- **AND** the recovered request is finalized and logged exactly once
