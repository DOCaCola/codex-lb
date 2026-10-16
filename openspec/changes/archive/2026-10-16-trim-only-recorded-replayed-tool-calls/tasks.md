# Tasks

## 1. Implementation

- [x] 1.1 Add `trim_replayed_previous_response_output` to `replay_safety.py`, matching calls by `call_id` and type
  against the anchored response's recorded calls.
- [x] 1.2 WebSocket route: trim only when `previous_response_id` is the continuity state's last completed response,
  using its recorded pending call types.
- [x] 1.3 HTTP bridge: trim only when `previous_response_id` is the durable row's latest response and the row holds a
  verified call manifest.
- [x] 1.4 Remove the shape-based trims, their predicates and their re-exports.

## 2. Verification

- [x] 2.1 Unit tests for the shared trim: recorded prefix, client-authored exchange, mixed prefix, type mismatch, and
  inputs without a trimmable echo.
- [x] 2.2 WebSocket integration test over a real first turn: recorded call trimmed, client-authored call kept, mixed
  prefix trimmed through the recorded call.
- [x] 2.3 HTTP bridge integration test where the first response emits the replayed `apply_patch_call`; unit test that
  a bridge request without a durable call manifest is forwarded unchanged.
