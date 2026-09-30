# Verification — 2026-09-30

Base: 131740e7b9381fb41a7fffbd1b19183a0207afa5.

- 358 regression tests passed in 91.42 seconds across Claude/provider-history,
  replay, protocol, inference, Chat, search, native history and compaction.
  One existing Starlette TestClient deprecation warning.
- Changed-file Ruff lint/format and ty check passed.
- make architecture-check passed: proxy architecture, cancellation safety,
  timing seams, settings tiers and migration topology. The existing repaired
  migration timestamp collision remains a warning, not a new migration.
- Strict change validation and git diff --check passed; application/test diff
  manually reviewed.

Both HTTP Responses paths, streaming/nonstreaming, preserve original ciphertext
through initial retention and a retained follow-up while only portable messages
and paired tools reach the mocked Claude transport. Both WebSocket paths also
verify retention. Unit tests cover opaque-only, blank summaries, mixed genuine
Claude/foreign state, index stability, malformed plaintext, external task turn
boundaries and content-free logging. Both compact endpoints still refuse foreign
ciphertext, with or without summaries, before account selection.

Tests use mocked inference, not live OAuth qualification or the exact production
request body. At verification time no live history, credentials, production
configuration or client fork was changed, and release had not started. Subsequent
archive, commit, push and deployment are explicitly authorized; deployment uses
the existing production upgrade.sh with readiness checks and a rollback image.
