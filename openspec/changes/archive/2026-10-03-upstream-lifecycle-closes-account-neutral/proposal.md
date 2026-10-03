# Keep upstream server-lifecycle closes account-neutral

## Why

OpenAI ends Responses WebSockets with close frames `1012` (service restart), `1001` (going away) and occasionally `1000` (normal closure) when the serving instance restarts or rotates. These closes describe the server instance, not the selected account. codex-lb nevertheless records a transient health error on the account for every such close that interrupts a pending request; only a `1000` close before any response event on the HTTP bridge is exempt.

Production, 2026-09-26 to 2026-10-03: 47 interrupted requests with close `1012` (42) or `1001` (5) out of about 63.6k native requests. Every conversation recovered on the client's next attempt, because Codex treats a server close as a retryable stream error and resends the full history on a fresh socket. 45 of 47 retries stayed on the same account; the two that moved lost most of their prompt cache.

References (inspected 2026-10-03):

- CLIProxyAPI `2044a01`: `isConnectionLifecycleError` exempts closes `1000`, `1001` and `1006` from credential cooldown (`connection_lifecycle_cooldown_test.go`). It also sends `1012` to its own clients as a reconnect request.
- sub2api `b8dece9`: an upstream read close of any code before downstream output reconnects and retries on the same account without an account penalty; after output it surfaces an error.
- opencodex `249462bf5`: an upstream close after send settles as a non-replayable 502 with no account penalty; the client retries.
- Codex `codex-api`: a close frame mid-stream is `ApiError::Stream` ("websocket closed by server before response.completed"), which is retried after the WebSocket session is reset, so the retry sends the full request.

## What Changes

- A received upstream close frame with code `1000`, `1001` or `1012` that interrupts pending requests no longer records an account-health error, on both the direct Responses WebSocket and the HTTP bridge, regardless of whether response events were already seen.
- The request outcome is unchanged: `stream_incomplete` with the close code in the message, downstream close semantics unchanged.
- Unchanged: replay eligibility, retry-circuit accounting, socket retirement, and the penalty for other close codes (for example `1011`) and incomplete close handshakes.

## Capabilities

### Modified Capabilities

- `responses-api-compat`: upstream websocket drop penalty excludes server-lifecycle close codes.

## Impact

- Account health and routing no longer react to OpenAI instance restarts; fewer avoidable account moves after such a close.
- `app/core/clients/proxy_websocket.py`, `app/modules/proxy/_service/websocket/mixin.py`, `app/modules/proxy/_service/http_bridge/upstream_events.py`, unit tests, responses-api-compat context notes.
