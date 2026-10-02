# Bind Proxy-Injected Anchors to Their Upstream Connection

## Why

Production still reports `previous_response_not_found` ("Previous response was not found; retry without previous_response_id.") on Codex conversations whose client never sent a `previous_response_id`. The proxy injected one.

Upstream keeps `store=false` responses only in the memory of the WebSocket connection that produced them. codex-lb injects a remembered response ID as `previous_response_id` after that connection has closed: on a WebSocket reconnect, on an HTTP bridge reattach from the durable row, and after session hydration. The new connection cannot resolve it, so upstream rejects the turn even though the account is unchanged. Account ownership was the wrong boundary; the connection is the real one.

## What Changes

- Every upstream connection gets an identity. A proxy-injected anchor records the connection that completed the response, and is valid only on that connection.
- WebSocket: at the send boundary, an injected anchor from another connection is withdrawn and the client's verified unanchored full replay is sent instead. When no verified replay exists, the turn fails closed locally with `previous_response_not_found` before anything reaches upstream.
- HTTP bridge:
  - a full resend on a fresh connection goes upstream unanchored and untrimmed;
  - a delta-only request on a fresh connection after a durable anchor fails closed locally with `bridge_previous_response_not_found`;
  - durable anchor hydration into new sessions and the pre-session durable anchor bind are removed;
  - every reconnect clears the session's completed-response state;
  - owner-forward recovery injects an anchor only when the local session completed that response.
- `last_completed_response_account_id` is replaced by the connection identity.

Client-supplied `previous_response_id` values are untouched. Same-connection anchoring and prefix trimming are unchanged.

## Capabilities

### Modified Capabilities

- `responses-api-compat`: proxy-injected anchors are scoped to the upstream connection that completed them, and the fresh durable HTTP bridge sends every full resend unanchored.

## Impact

- `app/modules/proxy/_service/support.py`: connection identities on WebSocket request/continuity state and on HTTP bridge sessions.
- `app/modules/proxy/_service/websocket/{helpers,mixin}.py`: anchor selection by connection, send-boundary withdrawal, local fail-closed error.
- `app/modules/proxy/_service/http_bridge/{helpers,request_submit,streaming,mixin}.py`: connection-scoped binding, withdrawal before send, fresh-reattach handling, reconnect reset.
- Behaviour: deltas that depended on a closed connection get a local 404 instead of an upstream one; full resends after a reconnect are sent whole, so they cost a cached full prompt instead of a failed turn.
