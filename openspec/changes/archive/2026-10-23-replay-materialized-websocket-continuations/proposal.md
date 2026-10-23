# Replay Materialized WebSocket Continuations

## Why

The pre-output hold and the accepted output-free replay never applied to normal Codex turns. Codex sends every
follow-up on its WebSocket as `previous_response_id` plus only the new items, and only after a failed stream does it
send the full history without an anchor. Such a delta has no retry-safe fresh body, so
`_websocket_request_has_replayable_body` was false, and both the hold and the replay were skipped. Production
request 1059501 (2026-10-23 07:53:50 UTC) was such a turn. All 8 overloads after the hold was deployed reached the
client, with zero replays across 323 WebSocket connections. Codex treats `server_is_overloaded` without retry advice
as terminal.

The 10-second hold was also too short: only 3 of those 8 refusals arrived within 10 seconds of acceptance. Across 13
production cases in 4 days, accepted overload refusals arrived 0.9 to 36.5 seconds after `response.created`.

A replay reconnects, and upstream resolves a `store=false` anchor only on the connection that produced it, so
re-sending the anchored body, which the client-anchored owner path did, cannot succeed. OpenCodex (#6969) holds the
prelude and replays on the same account and then on one alternate account; its sends are always self-contained.

## What Changes

- Direct WebSocket records the history of the last completed response (materialized input plus output) and of the
  last empty prewarm. A client delta anchored to a recorded response gets the history followed by the delta as its
  retry-safe fresh payload; the anchored request itself is forwarded unchanged.
- Replays of anchored requests always send the fresh payload. When the payload cannot leave the owner, it keeps the
  owner pin and goes to that owner.
- The client's next turn, anchored to the id it read for a replayed response, is sent as the recorded conversation
  plus its delta, because upstream never issued that id on the current connection.
- The pre-output hold is raised from 10 to 40 seconds.
- A refused replay of a replayable terminal is logged with its reason and without content.
- Output collected at a terminal is computed once and shared by HTTP replay storage, checkpoint retention and
  continuity history.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: adds continuity history recording for direct WebSocket; the pre-output hold lasts 40
  seconds and covers recorded client deltas; anchored direct WebSocket replays send the fresh body.

## Impact

- `app/modules/proxy/_service/support.py` (request and continuity state, hold duration).
- `app/modules/proxy/_service/websocket/mixin.py` (materialization, alias expansion, output collection, replay prep).
- `app/modules/proxy/_service/websocket/helpers.py` (history recording, anchored replay body).
- `app/modules/proxy/_service/http_bridge/accepted_replay.py` (refusal reasons and logging).
- Memory: one recorded history per open direct WebSocket connection. Image-heavy conversations can hold tens of MB.
- Each recorded client delta serializes its fresh payload, as proxy-injected anchors already do.
- A client that waits for `response.created` can wait up to 40 seconds while upstream is silent after acceptance.
