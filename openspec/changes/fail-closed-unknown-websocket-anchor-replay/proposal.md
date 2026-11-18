## Why

The proxy keeps an anchorless "fresh" copy of an anchored direct WebSocket
request so that it can recover when upstream answers
`previous_response_not_found` or closes before output. That copy is only
correct when the request's input is the full conversation.

`_websocket_client_previous_response_full_resend_is_retry_safe` compared the
input with stored context only when the anchor was the connection's last
completed response, and returned `True` for every other anchor. A Codex delta
(a user message, or a developer plus a user message) passes the structural
check, so after a miss the proxy replayed the delta alone. Upstream answered
without the thread's earlier context and the client saw a normal completion.

In this fork the same predicate also took precedence over the recorded-history
path, which completes a delta into the full conversation, and the delta was
then recorded as the turn's materialized input. A delta that restated the
previous delta was treated the same way.

Reported upstream as Soju06/codex-lb issue #2730, fixed in PR #2731.

## What Changes

- A client-anchored payload is a full resend only when its anchor is the
  connection's last completed response (or empty prewarm), that request's input
  covered its whole context, and the payload restates the stored input prefix.
  The predicate fails closed for anything else.
- The request state and the connection's continuity record whether a
  completed request's input covered its whole context: it had no anchor, the
  proxy injected the anchor, or it was a proven full resend. An injected
  session anchor inherits the coverage of the completion it points to.
- Client-anchored deltas on a known anchor now always use the recorded-history
  replay. An anchor this connection never completed has no history, so a
  pre-output `previous_response_not_found` reaches the client, which resends
  its complete history.
- A history replay is serialized like a client body with the same input. When
  the recorded history starts with the first turn's `additional_tools` item,
  the replay is a Lite body with the Lite marker, instead of a body with Lite
  reasoning but no marker that was recorded as non-Lite.

## Impact

- `app/modules/proxy/_service/websocket/helpers.py`,
  `app/modules/proxy/_service/websocket/mixin.py`,
  `app/modules/proxy/_service/support.py`.
- Tests: `tests/unit/test_proxy_utils.py`,
  `tests/integration/test_proxy_websocket_responses.py`.
- No settings, schema or API changes.
