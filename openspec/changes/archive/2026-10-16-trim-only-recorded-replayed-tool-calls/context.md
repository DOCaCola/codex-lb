# Context

## Incident

- Request `ws_d762588d1cb04148bd30ac26a82b7735`, 2026-10-15 22:30 UTC, Codex Desktop over the WebSocket route.
- The follow-up anchored on the previous response and carried Codex Desktop's own `visualization_state_*`
  `function_call` plus its `function_call_output`. The shape-based trim removed the call; upstream rejected the
  orphaned output with "No tool call found".

## References

- CLIProxyAPI, sub2api, opencodex, OmniRoute: forward `previous_response_id` deltas as sent; any pairing is by
  `call_id`. None strips leading items by shape.
- Upstream codex-lb and Frozen811/codex-lb carry the same shape-based trims as before this change; no upstream issue or
  PR covers this failure.

## Design notes

- Source of truth for "produced by the anchored response": the WebSocket continuity state's
  `last_pending_tool_call_types` (recorded at completion) and the HTTP bridge's durable
  `latest_pending_tool_calls` manifest (written while the completion is processed, before the client can follow up;
  absent when the manifest could not be verified).
- The trim cuts after the last recorded call, so a trailing assistant message or reasoning item after it is forwarded.
- An unattributable echo is forwarded whole. That is the pre-#651/#652 behaviour and what the references do; the
  upstream commits do not record which failure the trim was added for.
