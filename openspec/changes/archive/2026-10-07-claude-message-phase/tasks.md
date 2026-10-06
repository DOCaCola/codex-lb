# Tasks

## 1. Implementation

- [x] 1.1 `ResponsesProjection` keeps the translated message open until its phase is known, merges consecutive text
  blocks into one message, and closes it with the phase implied by the next block or the stop reason.
- [x] 1.2 `ResponsesProjection.interrupt` closes a finished message without a phase; upstream `error` events and the
  transport failure path deliver it before the error.

## 2. Verification

- [x] 2.1 Unit tests for phase by stop reason, text before a tool call, consecutive text blocks and an upstream error
  after text; integration tests for partial output before a projection failure still pass.
- [x] 2.2 ruff, pytest, strict OpenSpec validation.
- [x] 2.3 Closed mock lab, stock Codex 0.160.1 over WebSocket: Claude answers are recorded with `phase: final_answer`,
  and a `fork_turns: "all"` child of a Claude parent receives the parent's answer.
