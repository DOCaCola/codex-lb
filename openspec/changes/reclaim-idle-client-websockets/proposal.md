# Reclaim Idle Client WebSockets Under Pressure

## Why

codex-lb closes every client Responses WebSocket after 120 seconds without client traffic
(`proxy_downstream_websocket_idle_timeout_seconds`, added upstream in #372 to keep leaked sockets from filling the
WebSocket admission lane). The Codex client keeps one socket per thread across turns and chains every request onto
the previous response on that socket; it only notices the close at its next request, then reconnects and resends the
full history without `previous_response_id`. The close also fires mid-turn while the client runs a long tool or waits
for a subagent.

Production, seven days of native traffic: 2,110 requests followed a gap above 120 seconds. Same-account requests that
reused nearly all of their prefix fell from 91% at a 1-2 minute gap to 74% at 2-3 minutes and stayed near 78% to 15
minutes: a step at the timeout, not gradual cache ageing. Time to `response.created` rose from about 0.5 to 0.9-1.6
seconds. The lane holds 512 sockets; peak load was 37 conversations in an hour and 145 in a day, so it never filled.

opencodex keeps idle client sockets open indefinitely because of exactly this client behaviour, and reclaims its
least recently used idle socket only when its admission limit is full, protecting sockets with a running turn or
pending client tool results (opencodex `live-sideband.ts`, #7095). sub2api closes after a fixed 300 seconds without
tool awareness.

## What Changes

- Remove the timed idle close and the `proxy_downstream_websocket_idle_timeout_seconds` setting: environment field,
  dashboard column (dropped by migration), settings API fields, dashboard input and strings, documentation.
- Register client Responses WebSockets with a process-wide reclaimer. When the WebSocket lane is full, the admission
  middleware asks the least recently used idle socket to close and waits up to five seconds for its slot before
  returning the existing 429.
- A socket is idle only with no pending request, no unfinished terminal settlement and no client tool calls awaiting
  results. The socket's own receive loop performs the close under its send lock with the existing re-check and
  buffered-frame drain, using reason `Idle Responses websocket reclaimed`.
- Continuation after an upstream reconnect beneath a live client socket keeps its existing handling (OpenAI's
  60-minute connection cap already exercises it).

## Capabilities

### Modified Capabilities

- `responses-api-compat`: "Responses upstream websocket liveness is bounded" is removed and re-added as "Responses
  upstream websocket liveness uses a fixed bound", without the removed setting and its dashboard scenario.

### New Capabilities

None. `proxy-admission-control` gains "Idle client Responses WebSockets are reclaimed only under capacity pressure".

