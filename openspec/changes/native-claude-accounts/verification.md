# Verification: native Claude accounts

Verified locally on 2026-09-26. No production changes or live credentials used.

## Assessment

All 12 implementation tasks and all nine specification requirements have local
implementation and regression evidence. No known blocking implementation findings
remain from this review. Main specification and operational context are synced;
archive awaits operator confirmation.

| Requirement | Implementation and regression evidence |
| --- | --- |
| Encrypted enrollment | `credentials.py`, `identity.py`, `service.py`; credential validation, PKCE replay, duplicate authenticated identity, reconnect generation tests |
| Refresh ownership | `auth.py`, repository CAS; concurrent workers, ambiguous intent/restart and definitive rejection/backoff tests |
| Catalog and pooling | `client.py`, `routing.py`, `dispatch.py`; two-account scope, quota, affinity and unavailable-owner tests |
| Native Messages | `transport.py`, `native.py`, proxy routes; native body/ping/header fidelity, count tokens, upstream errors, truncated-stream native error and real transport cancellation tests |
| Responses adaptation | `protocol.py`, `responses.py`, `opaque.py`, `session.py`, shared continuation; HTTP/WS two-turn replay, tool/custom-tool/namespace, signed state, images, incomplete, compaction and TTL tests |
| Version following | `version.py`, scheduler; daily discovery, unchanged/stale checks, pin/unpin and immutable request profile tests |
| Unified controls | shared accounts/dashboard and `features/claude`; enrollment, consent, pause, privacy, read-only tests and desktop/mobile screenshots |
| Qualification boundary | main context and `docs/claude-accounts.md`; no paid fallback or hidden eligibility retry |
| OAuth request profile | `profile.py`, `request.py`; endpoint-specific headers, native preservation, explicit legacy/modern instruction placement, cache markers and stable session identity tests |

## Results

- Affected backend suite: **430 passed**. Includes all Claude tests plus shared
  forwarding, source dispatch and OpenRouter account regressions.
- Frontend full suite: **185 files, 1,679 tests passed**.
- Frontend TypeScript, ESLint and production build passed.
- Two Playwright unified-account screenshots passed at 1440px and 390px;
  desktop accounts and mobile reconnect UI visually inspected.
- Backend Ruff lint and formatting passed; application and Claude test type
  checks passed. Architecture, cancellation, timing and settings checks passed.
- Isolated SQLite upgrade/schema-drift/downgrade/reupgrade passed. Migration
  topology has one head (`20260925_030000_claude_identity`) and 267 revisions,
  checked against freshly fetched `origin/main`.
- Strict change and main-spec validation passed. `git diff --check` passed.

## Remaining qualifications

1. Live OAuth request acceptance, current model availability and included-plan
   billing are **not verified** by synthetic/loopback tests. Run a separately
   authorized live acceptance check before production rollout.
2. Whole-repository `ty check` reports nine existing errors in unchanged
   `test_openrouter_accounts.py`, `test_openrouter_images.py` and
   `test_openrouter_protocol.py`. These are nullable-row/invariant-JSON typing
   diagnostics, not Claude test failures; keep them separate from this feature.
3. Unsupported Responses controls fail explicitly as documented. Native Messages
   extensions do not imply Responses feature parity. Cache creation contributes
   to input usage but has no separate cache-write pricing ledger bucket.
4. Test output includes an existing AnyIO/Starlette deprecation warning.

Checkpoint commit: `6501fbef0` (`feat(claude): add quota-aware account selection`).
At verification time, the subsequent implementation was not yet committed,
pushed or deployed. Deployment does not establish live OAuth qualification.
