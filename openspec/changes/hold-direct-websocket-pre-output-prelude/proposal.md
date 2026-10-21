# Hold the Direct WebSocket Prelude Before Output

## Why

In production, all 17 `server_is_overloaded` errors of the last 14 days hit direct WebSocket requests after
`response.created`. codex-lb forwarded `response.created` (`sequence_number` 0) at once, and "Direct WebSocket
replay never mixes numeric response sequences" forbids replaying once a numeric sequence was sent. The accepted
output-free replay therefore never ran on direct WebSocket, and Codex treats `ServerOverloaded` as terminal, so users
saw "Our servers are currently overloaded".

OpenCodex holds empty `response.created` / `response.in_progress` / `response.queued` frames for at most 10 seconds
after sending and turns an overload during that hold into a replay (`preOutputRefusalHold`, OpenCodex #6969). Sub2API
`e068c3d02` treats `response.queued` and `response.metadata` as metadata that must not end the replay-safe window.
Of the 17 production overloads, 13 arrived within 10 seconds of `response.created`.

## What Changes

- A direct WebSocket request that is the socket's only pending request and can still be replayed holds
  `response.created` and later `response.in_progress`, `response.queued`, and `response.metadata` frames for at most
  10 seconds instead of sending them.
- The held frames are sent unchanged before the first other forwarded frame of the response, before a frame of another
  request, or when the hold deadline passes (the relay wakes for it). Sent held frames set the sequence watermark.
- An output-free failure during the hold is replayed by the existing accepted-replay machinery; the held frames remain
  the lifecycle the client reads, and the replay must advance beyond their last `sequence_number`.
- A synthesized terminal failure sends the held frames before the failure; only a capability-lineage persistence
  failure discards them. Keepalives treat a holding request as pre-created.
- `response.queued` and `response.metadata` no longer count as lifecycle events.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: adds the direct WebSocket pre-output hold; "Direct WebSocket replay never mixes numeric
  response sequences" and "Accepted output-free capacity failures are replayed within a single response lifecycle"
  account for held frames.

## Impact

- `app/modules/proxy/_service/support.py` (request state, hold helpers, `_record_response_event`).
- `app/modules/proxy/_service/websocket/mixin.py` (frame processing, forwarding, relay timer, keepalive).
- `app/modules/proxy/_service/http_bridge/accepted_replay.py` (shared replay-body predicate).
- The HTTP bridge is unchanged: it never records a downstream sequence watermark.
- A client that waits for `response.created` before sending its next request on the same socket can wait up to
  10 seconds while upstream is silent after acceptance.

