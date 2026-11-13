## Why

On 2026-11-13 from 12:33 UTC, Andy's Codex Desktop chat `01a14066-4115-73e1-a126-74acd4cd48a3` was stuck reconnecting. After OpenAI rejected one oversized turn, the client lost its incremental connection and had to resend the full history: about 133 MB, or about 100 MB compressed, at about 1.4–2 MB/s. Every attempt was closed after exactly 40 seconds, the uvicorn defaults `ws_ping_interval=20` plus `ws_ping_timeout=20`.

Uvicorn fails a WebSocket with 1011 when a ping goes unanswered, even while the client is still delivering frame bytes. The Codex websocket pump sends and receives in one loop, so it can't answer a ping until its current message has been fully written. As a result, any upload that takes longer than 40 seconds could never succeed.

codex-lb already judges upstream WebSocket liveness by any inbound frame. CLIProxyAPI pings downstream clients without a pong deadline, and opencodex disables the idle timeout.

## What Changes

- The listener uses a uvicorn WebSocket protocol subclass. Any inbound data received while a ping is outstanding satisfies that ping and schedules the next one.
- A client that sends nothing is still closed after `ws_ping_timeout`. Ping interval and timeout settings are unchanged.

## Impact

- Specs: `responses-api-compat`.
- Code: `app/core/websocket_protocol.py`, `app/cli.py`.
- No settings, schema or client changes.
