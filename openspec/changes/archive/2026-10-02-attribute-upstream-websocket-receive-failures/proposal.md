# Attribute Upstream WebSocket Receive Failures

## Why

After the native WebSocket message queue was byte-budgeted, three `stream_incomplete` turns on 2026-10-02 still failed with "Upstream websocket closed before response.completed: Upstream websocket receive failed", each before any output. Their cause could not be established. The native helper reduced every post-connect failure to "transport failed" or "protocol failed" and discarded the underlying error. The request log left `failure_phase` and `failure_detail` empty on the WebSocket path. The terminal-failure log write also omitted the response-created and first-upstream-event timings, so the log could not show whether upstream had accepted the turn. The only attribution was a container log line, which a redeploy discards.

## What Changes

- The native helper's `websocket_error` event carries an optional `failure_detail`. It is the payload-free snake_case name of the underlying error variant, for example `io_connection_reset`, `protocol_reset_without_closing_handshake`, or `capacity_message_too_long`.
- Python carries the detail on the transport error and the receive-error message. The aiohttp adapter uses the exception class name.
- When a terminal receive error is not replayed, the direct WebSocket and HTTP bridge owners record its phase and detail as the request's `failure_phase` and `failure_detail`. An earlier, more specific attribution is kept.
- Terminal failure rows record `latency_response_created_ms` and `latency_first_upstream_event_ms`.
- The once-per-connection receive warning reports `failure_detail` in place of `queue`. A queue overflow reports its queue name as the detail.

## Capabilities

### Modified Capabilities

- `responses-api-compat`: native receive diagnostics and request-log attribution of upstream WebSocket failures.

## Impact

- `crates/codex-lb-protocol`, `crates/codex-lb-egress`: the event field and variant naming.
- `app/core/clients/native_egress.py`, `app/core/clients/proxy_websocket.py`: carrying the detail.
- `app/modules/proxy/_service/websocket/` and `http_bridge/upstream_events.py`: request attribution and the terminal log write.
- No public error, replay, or account-health behavior changes. No schema change: the columns already exist.
