# Verification — 2026-09-30

## Completeness and correctness

All four tasks are complete. The added requirement is synced to the main
model-source-routing specification and its context document. No unresolved
correctness or design findings remain in the scoped review.

- Shared source projection distinguishes payload-free local markers from opaque
  checkpoints, preserves visible input order, and publishes no partial input on
  failure. Native marker handling retains its existing serialization policy.
- Public HTTP inference covers both Responses paths, streaming and nonstreaming,
  retained continuation, and readable tool pairs. WebSocket coverage exercises
  both paths, continued replay, and terminal compaction. Dedicated compact paths
  cover direct and retained input and original error indexing before control-item
  removal. Compatible Responses sources are also exercised through local stubs.
- Unit coverage verifies missing/null ciphertext, supported metadata, exact
  summary/tool/image preservation, proxy summary lowering, invalid/opaque/corrupt
  items, unsupported marker fields including proxy-prefixed ciphertext, atomic
  rejection, and content-free success/error diagnostics.

## Results

- Final regression run: **507 passed**, one existing Starlette/AnyIO deprecation
  warning. Suites include compaction markers/compatibility, Claude/native
  provider history, complete source compaction, Claude inference/routing,
  source forwarding/dispatch and WebSocket bridge/guard behavior.
- Ruff check and format check passed for both implementation files and both new
  test files. Focused `ty check` passed for the same files.
- `make architecture-check` passed all proxy, cancellation, timing, settings-tier
  and migration-topology checks. The existing explicitly merged migration
  timestamp collision produces a warning, not a failing gate.
- Strict change and main model-source-routing validation passed. The main-spec
  validation run passed all 74 specifications.
- `git diff --check` and manual scoped code/spec/test review passed.

## Qualification boundary

Tests use isolated local stubs, not production inference. The production
2026-09-30T16:53:37Z failure did not capture item subtype or request body, so it
is not established that the reported request contained only a local marker.
Genuine encrypted native checkpoints remain nonportable and are rejected rather
than silently losing context. Improved diagnostics will distinguish those cases.

No client fork, live-history edit, schema/configuration change, commit, push or
deployment was performed. Concurrent API-key/dashboard work remains outside this
change and was not modified.
