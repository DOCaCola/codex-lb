# Tasks

## 1. Implementation

- [x] 1.1 Add the preserved-thinking model and thinking-mode predicate to `capabilities.py`.
- [x] 1.2 Add `bind_replayed_thinking` to `recovery.py` and apply it in dispatch for every endpoint.
- [x] 1.3 Send the binding-controls beta whenever the projected body carries `thinking.block_binding`.
- [x] 1.4 Log non-empty `input_transformations` from streaming `message_start` and non-streaming responses with the
  cache-lineage comparison.

## 2. Verification

- [x] 2.1 Unit tests for model and thinking-mode eligibility, unsigned and redacted history, and caller-chosen behavior.
- [x] 2.2 Integration test: native Opus 5.5 replay carries `drop_block` and the beta; a request without signed history
  carries neither.
- [x] 2.3 Unit tests for the binding report with and without a previous request; integration tests for streaming and
  non-streaming reports.
