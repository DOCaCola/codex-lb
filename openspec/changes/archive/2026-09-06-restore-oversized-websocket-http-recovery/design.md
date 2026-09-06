# Design: Restore oversized WebSocket request recovery

## Decision

Choose the rejection status from the incoming request transport. A request
state with `transport = "websocket"` receives `413`; every other transport
retains `400`.

The error remains local because the request is larger than codex-lb's configured
upstream WebSocket budget. The official Codex client maps the wrapped `413`
error event to a retryable HTTP-status error. After its configured stream retry
budget, it disables WebSockets for that client session and resubmits through
HTTPS. codex-lb already keeps native Codex HTTP requests on the upstream HTTP
transport, so the fallback request is evaluated by the upstream HTTP endpoint
instead of the WebSocket-size guard.

## Constraints

- The status does not assert that the upstream HTTP endpoint will accept the
  request; it restores the client's opportunity to receive that endpoint's
  actual result.
- The client currently retries the WebSocket request before falling back and
  keeps HTTP fallback enabled for the rest of its session. Those are client
  semantics and are not changed here.
- HTTP callers keep the terminal `400` contract because they cannot recover by
  changing their already-HTTP transport.
