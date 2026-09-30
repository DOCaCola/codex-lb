# Verification — 2026-09-30

Base: ca9ec9458c463d866870cb930f017f99870b9f5c.

## Passed

- 339 unit/integration tests across provider-history, Claude replay/protocol,
  inference, Chat, search, native provider-history and complete source compaction.
  One existing Starlette TestClient deprecation warning.
- Changed-file Ruff lint and formatting; changed-file ty check.
- make architecture-check: proxy architecture, cancellation safety, timing seams,
  settings tiers and migration topology. The existing repaired migration timestamp
  collision remains a warning, with the explicit published merge intact.
- Strict change validation and all 74 main specifications.
- git diff --check and manual application/test diff review.

Whole-repository ty check is not clean: 484 diagnostics on this worktree and
484 on an isolated detached worktree of the unchanged base, using the same
interpreter. Changed application and test files pass their focused type check.

## External path coverage

Both public HTTP Responses paths are tested streaming and nonstreaming; both
WebSocket paths cover conversion and indexed refusal. Retained continuation
preserves the original ciphertext while only portable text reaches the mocked
Anthropic transport. Both compact paths preserve plaintext history; complete
compaction refuses foreign ciphertext. Tests cover actual Opus 5.5 catalog
capabilities, unchanged adaptive thinking/medium effort, genuine empty-display
signed replay, paired tools, tampering, fork scope and stable error indices.

These are deterministic mocked upstream tests, not a live OAuth inference or a
capture of the exact failed client request. No client fork or live history edit
is part of this change. Opaque-only or active foreign state cannot be projected
losslessly and is explicitly rejected, not silently deleted.

## Delivery

Archive, commit under DOCa Cola, fast-forward fork main, push and deploy through
the existing production upgrade.sh are authorized. Delivery follows verification;
this artifact does not pre-claim successful production activation. The existing
script performs disposable migration/readiness tests and keeps a rollback image.
