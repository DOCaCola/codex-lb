# Verification and operational notes

## Scope and rationale

Operation refinement reuses successful routing validation, not extra request-body
parsing, prompt matching or client classification headers. HTTP uses the existing
terminal-compaction routing decision; native websocket preparation retains the
raw validator's boolean result before history normalization. Source websocket
dispatch uses the existing HTTP pipeline in a separate turn task.

The operation is independent of workload. In particular, a native websocket
compaction and an internal compact call can retain the existing Normal workload
while displaying Compaction. Image adapter operations remain unchanged.

## Failure and isolation checks

Public-path regressions cover native HTTP, Claude and native OpenRouter synthetic
compaction, compatible sources, normal/compact/normal websocket sequences, invalid
triggers, historical checkpoints and forged client classification claims.
Nested native checkpoint handoffs retain their own label and restore the parent's
operation/request ID on success, errors, timeout and cancellation. Concurrent
parent contexts remain unchanged. Signed owner-forwarding tests cover Compaction
and Checkpoint handoff as well as image operations.

Example: a provider-switch compaction produces Compaction → Checkpoint handoff →
Compaction logs without relabeling the auxiliary native request as its parent.
No new log producer, accounting change or historical backfill is introduced.

## Verification

- Latest semantic unit/public-path suite: 90 passed.
- HTTP handoff, automation and semantic public-path suite: 142 passed.
- Compatibility run covering operation persistence, compact routing, history,
  source completeness, images and signed forwarding: 555 passed; one new test
  expected a changed workload incorrectly. Its expectation was corrected to
  Normal, then passed in both subsequent dedicated suites above.
- Dashboard labels, parsing and existing request-table tests: 108 passed.
- Changed Python paths: Ruff check passed; diff whitespace check passed.
- Frontend type checking passed.
- Strict change validation and all 75 main specs passed.

Existing Starlette deprecation, test SQLite shutdown and frontend runtime
warnings do not affect these assertions. Main attribution spec/context are
synced. Verification used local stubs; no live paid request or deployment was
performed. Archiving and committing were subsequently authorized separately.
