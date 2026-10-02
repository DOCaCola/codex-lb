# responses-api-compat Delta

## ADDED Requirements

### Requirement: Upstream WebSocket receive failures are attributed on the request log

When a terminal upstream WebSocket receive error fails a turn without transparent replay, the direct WebSocket and HTTP bridge relay owners MUST record the failure's phase as `failure_phase` and its underlying error as `failure_detail` on that turn's request log, unless the turn already carries a failure attribution. The native helper MUST name the underlying error by its variant only, never by payload, URL, header, or message text. Terminal failure rows MUST record `latency_response_created_ms` and `latency_first_upstream_event_ms` when observed. A replayed turn MUST NOT inherit the failed socket's attribution.

#### Scenario: Upstream drops the connection without a close frame

- **WHEN** upstream drops the TCP connection mid-turn without a close frame, and the turn is not replayed
- **THEN** the request log records `failure_phase` `protocol` and `failure_detail` `protocol_reset_without_closing_handshake`
- **AND** it records whether `response.created` had been received

#### Scenario: An earlier attribution is kept

- **WHEN** a turn already carries a failure attribution before the receive error
- **THEN** the request log keeps that attribution

## MODIFIED Requirements

### Requirement: Native WebSocket receive diagnostics preserve safe provenance
The native WebSocket adapter MUST emit at most one warning per connection when a native receive exception is surfaced, identifying the opening request ID, an allowlisted failure phase, and a failure detail: the payload-free underlying error name, or the local queue name if the failure originated from a bounded queue. Unknown phase values MUST be reported as unknown. Expected cancellation and successful receives MUST NOT emit this warning. The warning MUST NOT include exception prose, payloads, headers, URLs, or credentials. Emitting the warning MUST NOT itself change public error envelopes or recovery decisions.

#### Scenario: Backpressure failure retains its queue provenance
- **WHEN** a local native WebSocket message queue overflows
- **THEN** the receive warning identifies consumer_backpressure and websocket_messages
- **AND** repeated receives do not duplicate that warning

#### Scenario: Untrusted error text is excluded
- **WHEN** a native failure contains sensitive prose or an unknown phase
- **THEN** the warning omits the prose and renders the phase as unknown
