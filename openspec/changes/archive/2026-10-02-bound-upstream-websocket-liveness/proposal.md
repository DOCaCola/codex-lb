# Bound Upstream WebSocket Liveness Independently

## Why

On 2026-10-02 at 13:42:23 UTC a reused upstream Responses WebSocket died silently. codex-lb took 109 seconds to declare it dead, and the client could only retry after that. The upstream pong deadline is borrowed from `proxy_downstream_websocket_idle_timeout_seconds` (120 s), a client-side idle policy. With pings every 20 s, the worst case from death to detection is 140 s on the direct path. The routed path derives a 120 s ping interval and a 60 s pong timeout from the same setting, for a worst case of 180 s.

The native helper also clears the pong deadline only on the matching pong. A connection that is busy streaming output can be declared dead when its pong is delayed behind data, a risk that grows as the bound tightens.

The references bound upstream liveness with a fixed transport constant: sub2api waits 10 s for a pong, and opencodex treats any inbound frame as proof of life. Codex CLI keeps its own 300 s stream idle timeout and retries on a fresh connection with the full input, so a faster upstream verdict lets the client's existing recovery start sooner.

## What Changes

- A fixed upstream liveness bound: ping every 20 s, and declare the connection dead 30 s after a ping when no frame arrives. It is a constant, not a setting, and no longer derives from the downstream idle timeout.
- The native helper treats any inbound frame as proof of life and clears the pending pong deadline.
- The bound applies to every upstream transport: the native helper on direct and routed connections, the Python `websockets` fallback, and the aiohttp routed fallback. aiohttp exposes a single heartbeat value and waits half of it for the pong, so it is given 60 s to keep the 30 s pong bound.
- The dashboard description of the downstream idle timeout no longer claims it controls upstream liveness.

No change to error codes, replay, account health, or request-log attribution. codex-lb adds no retry: the client already retries on a fresh connection with its full input.

## Capabilities

### Modified Capabilities

- `responses-api-compat`: upstream WebSocket liveness uses a fixed bound independent of the downstream idle timeout.

## Impact

- `crates/codex-lb-egress/src/websocket.rs`: any inbound frame clears the pong deadline.
- `app/core/clients/codex.py`: the `UpstreamWebSocketLiveness` policy and its mapping to native and aiohttp transports.
- `app/core/clients/proxy_websocket.py`: direct and routed connections use the policy.
- `frontend/src/i18n/locales/*.json`: the idle timeout description.
