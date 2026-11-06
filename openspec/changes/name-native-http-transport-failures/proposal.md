# Name native HTTP transport failures

## Why

A native HTTP upstream failure was logged as the bare message "native upstream
request failed", with `failure_phase` and `failure_detail` empty. When the
turn was a WebSocket turn sent over HTTP (`reason=frame_size`), the row also
said `upstream_transport=websocket`. The one production occurrence
(2026-11-06 12:19:56 UTC, Andy Beta, gpt-6-astra) could not be attributed.
The HTTP relay also forwarded the internal synthetic-failure marker to the
WebSocket client.

## What Changes

- The native egress helper names the failure from the error's source chain
  (I/O kind, h2 reason, hyper kind, TLS variant) without payload, URL or header
  text, and sends it as `failure_detail` on its error event.
- The Python native client and the HTTP stream path keep that phase and detail
  on the locally generated terminal.
- The WebSocket HTTP relay carries the attribution to the request log, records
  `upstream_transport=http` for the turn it ends, and strips the internal
  marker from the client frame.

## Impact

Native egress helper (Rust), native client, HTTP stream path and WebSocket HTTP
relay. Logging only; no routing or retry behaviour changes. Pins `h2` as a
direct dependency of the egress crate to read its error reasons.
