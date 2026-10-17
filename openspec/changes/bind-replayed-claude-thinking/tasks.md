# Tasks

## 1. Implementation

- [x] 1.1 Add the preserved-thinking model and thinking-mode predicate to `capabilities.py`.
- [x] 1.2 Add `bind_replayed_thinking` to `recovery.py` and apply it in dispatch for every endpoint.
- [x] 1.3 Send the binding-controls beta whenever the projected body carries `thinking.block_binding`.

## 2. Verification

- [x] 2.1 Unit tests for model and thinking-mode eligibility, unsigned and redacted history, and caller-chosen behavior.
- [x] 2.2 Integration test: native Opus 5.5 replay carries `drop_block` and the beta; a request without signed history
  carries neither.
