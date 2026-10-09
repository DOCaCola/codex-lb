## 1. Specify the contract

- [x] 1.1 Add Responses compatibility requirements for native sanitation,
      synthetic output, and replay lowering.
- [x] 1.2 Add model-source routing requirements for terminal compaction.

## 2. Implement the behavior

- [x] 2.1 Add codex-lb compaction envelope encode/decode and replay lowering.
- [x] 2.2 Add native subscription-boundary reasoning sanitation.
- [x] 2.2a Remove lookup-only item IDs at every stateless Responses boundary.
- [x] 2.2b Apply native sanitation to direct WebSocket, HTTP-session bridge,
      and prepared replay serialization.
- [x] 2.3 Build source summarization requests and validate completed summary
      output.
- [x] 2.4 Route terminal source compaction through the synthetic lifecycle.

## 3. Verify

- [x] 3.1 Add unit tests for envelope handling, native sanitation, and source
      request/result transformation.
- [x] 3.2 Add route-level regression coverage for source-owned terminal
      compaction and native subscription compaction.
- [x] 3.2a Add direct WebSocket and bridge serialization regressions for a
      source-to-native model transition.
- [x] 3.3 Run focused tests, lint/type checks, architecture checks, and strict
      OpenSpec validation.
