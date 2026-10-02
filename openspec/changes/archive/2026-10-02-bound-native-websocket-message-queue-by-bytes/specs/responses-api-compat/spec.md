# responses-api-compat Delta

## ADDED Requirements

### Requirement: Local WebSocket relay backpressure is account-neutral

When a native upstream WebSocket fails with `consumer_backpressure`, the adapter MUST surface `local_websocket_backpressure` and treat it as an account-neutral transport code. The direct WebSocket and HTTP bridge relay owners MUST fail the affected pending turns terminally, without transparent replay and without an account-health penalty. The public error message MUST identify codex-lb's relay as the cause and MUST NOT describe an upstream close.

#### Scenario: Relay backpressure fails the turn without blaming the account

- **WHEN** a native WebSocket message queue overflows during a turn
- **THEN** the pending turn fails with `local_websocket_backpressure`
- **AND** the turn is not replayed
- **AND** the selected account records no transient error
- **AND** the error message does not say that upstream closed the WebSocket

## MODIFIED Requirements

### Requirement: Native WebSocket receive diagnostics preserve safe provenance
The native WebSocket adapter MUST emit at most one warning per connection when a native receive exception is surfaced, identifying the opening request ID, an allowlisted failure phase, and the local queue name if the failure originated from a bounded queue. Unknown phase values MUST be reported as unknown. Expected cancellation and successful receives MUST NOT emit this warning. The warning MUST NOT include exception prose, payloads, headers, URLs, or credentials. Emitting the warning MUST NOT itself change public error envelopes or recovery decisions.

#### Scenario: Backpressure failure retains its queue provenance
- **WHEN** a local native WebSocket message queue overflows
- **THEN** the receive warning identifies consumer_backpressure and websocket_messages
- **AND** repeated receives do not duplicate that warning

#### Scenario: Untrusted error text is excluded
- **WHEN** a native failure contains sensitive prose or an unknown phase
- **THEN** the warning omits the prose and renders the phase as unknown
