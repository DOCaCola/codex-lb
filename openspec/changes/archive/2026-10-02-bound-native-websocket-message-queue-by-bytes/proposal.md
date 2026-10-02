# Bound the Native WebSocket Message Queue by Bytes

## Why

Each native upstream WebSocket has two local queues: the helper reader's per-request event queue (bounded by a 32 MiB byte budget and 4096 events since #2173), and a per-WebSocket message queue that the pump fills for the relay. #2173 left the message queue at 64 messages because it had not tripped in production. It now trips: on 2026-10-02 between 08:07 and 10:00 UTC, production logged 14 `native_websocket_receive_failed failure_phase=consumer_backpressure queue=websocket_messages` warnings. They spanned both active accounts and two unrelated clients, and the event loop showed no lag. A healthy relay that briefly pauses during a burst of hundreds of reasoning deltas overflows 64 slots, which is the same failure that #2167 fixed for the event queue.

Each overflow also blamed upstream. The adapter mapped `consumer_backpressure` to the generic `upstream_unavailable` fallback, so relay owners recorded `stream_incomplete` with "Upstream websocket closed before response.completed" and a transient account-health penalty. The relay was still eligible to replay the turn. The fault is local: upstream did nothing wrong, and the request was still running there.

## What Changes

- The native WebSocket message queue uses the same byte-budgeted queue as the event queue: 32 MiB of queued message payload and 4096 messages. The fixed 64-message cap is removed. The pump stays non-blocking, so send acknowledgements keep resolving while messages wait for the relay.
- A residual overflow, meaning a relay that has stopped draining, fails the WebSocket with a dedicated account-neutral code, `local_websocket_backpressure`. Relay owners fail the pending turn terminally, without replay and without an account penalty. The public message names codex-lb's relay, not upstream.

## Capabilities

### Modified Capabilities

- `outbound-http-clients`: native WebSocket message queue bound.
- `responses-api-compat`: classification of local WebSocket relay backpressure; native receive diagnostics no longer promise an unchanged recovery decision for backpressure.

## Impact

- `app/core/clients/native_egress.py`: the generic byte-budgeted queue, WebSocket message sizing, and removal of the 64 cap.
- `app/core/clients/proxy_websocket.py`: backpressure classification and the account-neutral set.
- `app/modules/proxy/_service/websocket/helpers.py`: the disconnect message for local backpressure.
- Tests in `tests/unit/test_native_egress.py` and `tests/unit/test_proxy_websocket_client.py`.
- Worst-case memory per native WebSocket rises from 64 messages to 32 MiB. Bytes are released as the relay drains. Clients see a different error code on the rare residual overflow; Codex treats unknown codes as retryable, so automatic client retry is unchanged. No settings, schema, or API changes.
