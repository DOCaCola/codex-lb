# Trim Only Recorded Replayed Tool Calls

## Why

On 15 Oct 22:30 UTC, request `ws_d762588d1cb04148bd30ac26a82b7735` failed upstream with "No tool call found for function
call output". Codex Desktop had continued a turn with `previous_response_id` and reported its own local
`visualization_state_*` exchange: a `function_call` the anchored response never produced, plus its output. The
WebSocket replay trim removed every call-shaped item ahead of the first tool output, including that client-authored
call, so upstream received an output with no call.

Both trims (WebSocket and HTTP bridge, from upstream #651/#652) decide by item shape. The HTTP variant additionally
accepts any `id` or `status` as proof of replay, which a client-authored item can carry too. Neither knows which
calls the anchored response produced, although both routes already record exactly that. CLIProxyAPI, sub2api,
opencodex and OmniRoute never strip a `previous_response_id` delta; where they pair items they do so by `call_id`.

## What Changes

- One shared trim drops the leading echo of the anchored response only through the last tool call that response
  recorded (same `call_id` and call type). Reasoning and assistant messages between them are part of the echo. The
  first call it did not produce, or any other item, ends the trim.
- The WebSocket route trims only when the request anchors on the connection's last completed response and uses its
  recorded call types. The HTTP bridge trims only when the request anchors on the durable bridge row's latest response
  and that row holds a verified call manifest. Otherwise the input is forwarded unchanged.
- The shape-based trims and their helpers are removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: "Interrupted tool calls receive synthetic outputs on anchored follow-ups" gains the
  identity-matched trim rule and an updated apply_patch trim scenario.

## Impact

- `app/modules/proxy/replay_safety.py` (`trim_replayed_previous_response_output`).
- `app/modules/proxy/_service/websocket/mixin.py`, `app/modules/proxy/_service/http_bridge/streaming.py` (callers).
- Removed: `_trim_websocket_previous_response_input_items`, `_is_websocket_previous_response_output_item`,
  `_trim_http_bridge_previous_response_input_items`, `_is_http_bridge_previous_response_output_item`,
  `_has_http_bridge_response_output_marker`, `_http_bridge_input_item_type` and their re-exports.
- An anchored follow-up whose echo cannot be attributed is forwarded whole, as every request was before #651/#652 and
  as all four references forward it.
