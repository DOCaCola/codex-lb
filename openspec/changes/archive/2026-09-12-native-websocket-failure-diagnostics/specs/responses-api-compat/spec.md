## ADDED Requirements

### Requirement: Native WebSocket receive diagnostics preserve safe provenance
The native WebSocket adapter MUST emit at most one warning per connection when a native receive exception is surfaced, identifying the opening request ID, an allowlisted failure phase, and the local queue name if the failure originated from a bounded queue. Unknown phase values MUST be reported as unknown. Expected cancellation and successful receives MUST NOT emit this warning. The warning MUST NOT include exception prose, payloads, headers, URLs, or credentials. Public error envelopes and recovery decisions MUST remain unchanged.

#### Scenario: Backpressure failure retains its queue provenance
- **WHEN** a local native WebSocket message queue overflows
- **THEN** the receive warning identifies consumer_backpressure and websocket_messages
- **AND** repeated receives do not duplicate that warning

#### Scenario: Untrusted error text is excluded
- **WHEN** a native failure contains sensitive prose or an unknown phase
- **THEN** the warning omits the prose and renders the phase as unknown
