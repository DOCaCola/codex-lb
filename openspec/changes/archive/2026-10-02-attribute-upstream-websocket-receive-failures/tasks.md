# Tasks

## 1. Native helper

- [x] 1.1 Add optional `failure_detail` to the `websocket_error` event, named by error variant without payload.

## 2. Attribution

- [x] 2.1 Carry the detail on `NativeEgressTransportError` and `UpstreamWebSocketMessage`. Report it in the receive warning.
- [x] 2.2 Record phase and detail on non-replayed requests for the direct WebSocket and HTTP bridge owners. Keep an earlier attribution.
- [x] 2.3 Record response-created and first-upstream-event timings on terminal failure rows.

## 3. Tests

- [x] 3.1 A TCP drop without a close frame emits `protocol_reset_without_closing_handshake`. An oversized message emits `capacity_message_too_long`.
- [x] 3.2 The helper event's detail reaches the transport error.
- [x] 3.3 A failed request's log row carries phase, detail, and timings. An earlier attribution is kept.
