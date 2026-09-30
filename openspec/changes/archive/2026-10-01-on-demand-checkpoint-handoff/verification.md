# Verification: on-demand-checkpoint-handoff

Verified locally on 2026-10-01 against HEAD `4cbc09573`. No commit, push,
archive, production deployment or live upstream request was performed.

## Completeness

All five implementation tasks complete. Both delta requirements are implemented
and synced to `openspec/specs/model-source-routing/spec.md`; rationale, bounds,
failure modes, examples and inspected reference revisions are in its context.

## Correctness

- `checkpoint_history.py` observes successful native compact completion without
  storing its input; native WebSocket completion also captures provenance from
  output events, including continuation deltas without readable replay input.
- `checkpoint_handoff.py` implements digest/key/conversation scope, private
  bounded origins and summaries, cache-first reuse, permission rechecks,
  cross-worker claims, expiry, failure and cancellation ownership. Cancellation
  during SQLite acquisition waits for the result and releases any acquired claim.
- `_source_checkpoint_resolver` generates with the recorded model/account using
  ordinary native reservation, admission, metering and logging. Synthetic request
  headers remove destination affinity and continuation state. Native auxiliary
  and destination request IDs are linked without logging content.
- Streaming's internal required-account pin cannot be cleared by owner-recovery
  branches. A paused owner, restricted owner/model, and transient native failure
  with a healthy backup all stop source dispatch rather than moving the checkpoint.
- Source preparation handles HTTP/WS inference, source continuation, synthetic
  compaction and generic OpenAI-compatible sources. The destination receives only
  valid completed summary text and the untouched visible suffix.
- Native operation, readable/portable inputs and existing snapshots require no
  auxiliary summary. Invalid/refused/incomplete/empty/tool output, timeouts,
  missing provenance and failed summary publication do not dispatch partial context.

## Local checks

- **303 passed**: checkpoint handoff/history, compaction compatibility,
  HTTP continuation, native/Claude provider history, compact/trigger routing,
  source compaction completeness and native affinity HTTP/WS integration suites.
- **127 passed**: native streaming/retry, API-key and cancel-safe utility tests.
- **320 passed, 10 failed**: wider owner/pinned/checkpoint selection from proxy
  utility and HTTP-bridge suites. The ten failures report missing `model_sources`
  tables in unit fixture databases. All ten reproduce on an unchanged HEAD
  archive; the archive-only git-grep test also fails because it has no `.git`.
  Those fixture problems are not corrected by this scoped change.
- Changed-file Ruff lint/format and app-module ty checks pass.
- Timing-seam and cancellation-safety gates pass; `git diff --check` passes.
- Strict change validation passes; strict main-spec validation: **74 passed**.
- Global architecture gate has the same three failures on unchanged HEAD:
  `service.py` 2603/2600, `load_balancer.py` 3038/3021,
  `http_bridge/mixin.py` 2472/2436. This change does not increase the streaming
  mixin's existing 1100-line size or relax any architecture allowance.
- Whole-app ty has six existing reasoning-policy diagnostics in untouched
  accounts, Claude routing and OpenRouter catalog/routing modules. Changed-module
  type checks are clean. An existing Starlette deprecation warning remains.

## Coherence and qualification

Storage reuses private atomic integrity-checked replay files, with separate origin
and summary namespaces and existing periodic maintenance. There is no primary
database migration, new operator setting, client fork or native transcript archive.
Native handoff persistence uses the existing tracked detached lifecycle: reservation
cleanup/settlement and log tasks can outlive response completion, remain owned and
are drained in cancellation/accounting tests. It does not impose a new synchronous
database flush on ordinary responses.

No critical local implementation/spec issues remain. Full global gates are not
green because of the baseline issues above. Real native ciphertext acceptance,
OAuth account/model eligibility and summary fidelity still require a live test.
Mocks establish routing and safety, not those upstream properties. This is not an
implementation inherited from any reference; their native-blob omission or
placeholder behavior is deliberately not adopted.

Unobserved legacy checkpoints still need complete readable input or a fresh native
compact observed after rollout. No ownership is guessed. Summary/provenance are
retained for at most 30 days and may be evicted earlier under documented byte and
entry bounds. Summaries are lossy and additional native usage is metered only when
generation is actually required. Archive awaits user confirmation.
