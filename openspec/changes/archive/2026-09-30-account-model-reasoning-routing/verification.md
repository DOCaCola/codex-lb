# Verification: account-model-reasoning-routing

Verified locally on 2026-09-30 against checkout HEAD `4586ad7a6` plus this change.
No commit, push, production configuration update, or deployment was performed.

## Completeness and correctness

All six implementation tasks and all three delta requirements are implemented.
The delta requirements and stable rationale are synced into
`openspec/specs/account-model-controls/{spec.md,context.md}`.

| Requirement | Implementation | Regression evidence |
| --- | --- | --- |
| Per-model reasoning eligibility | Shared pure policy in `app/core/model_routing.py`; native account persistence/routing snapshots; provider typed state and source projection; native load balancer, Claude selection and OpenRouter source filtering | `test_model_reasoning_policy.py`, `test_account_model_controls.py`, `test_openrouter_accounts.py`, `test_claude_routing.py` |
| Fresh, sticky, owned and reused transport enforcement | Eligibility precedes scheduling; native HTTP/WS reuse and submit checks; source ownership remains distinct from eligibility; provider failover and Claude 401 recovery preserve requested effort | `test_proxy_http_bridge.py`, `test_proxy_websocket_responses.py`, Claude inference dispatch matrix and auth-recovery tests |
| Explicit none, default omission and normalization | Explicit none remains an effort; unknown defaults fail closed only for restricted accounts; internal request provenance retains minimal through existing wire normalization; native client ultra is configured as its max wire effort | Pure policy and request-policy tests; native wire-effort API test; `test_stream_account_policy_uses_requested_effort_before_wire_normalization` covers backend and v1 HTTP routes; parallel bridge compatibility test |
| Durable unavailable model configuration | Original saved membership/reasoning IDs validate atomic edits; catalog availability is separate; provider all mode retains disabled claims for vanished configured IDs; internal account allowlists are omitted from client catalogs | Native plan downgrade/restore, provider missing-catalog/reselect tests and catalog projection tests |
| Dialog-local model mode | Shared reasoning checkbox dropdown; All models is inside conversation dialogs; atomic drafts/save; cancelled drafts do not persist; image dialog remains separate | Five component test files, TypeScript, production build, desktop/mobile Playwright tests and screenshot inspection |

## Local validation evidence

- Policy/account/catalog/routing batch: **641 passed**.
- Transport/inference/authentication batch: **1,370 passed**, one timeout, one
  known-baseline test deselected. The timeout was
  `test_websocket_claude_roundtrip_and_continuation[429-False-/v1/responses]`;
  event-loop starvation was recorded, and an isolated rerun **passed**.
- Latest native account/catalog/warm bridge batch: **100 passed**.
- Additional requested-effort HTTP route tests: **2 passed**; parallel/warm bridge
  tests after final review: **2 passed**.
- Final raw HTTP Responses integration suite (including the new backend/v1
  policy regressions): **103 passed**.
- Frontend component tests: **47 passed** across five files.
- TypeScript, changed frontend ESLint, Vite production build, Ruff lint/format and
  `git diff --check` passed. Formatting-only changes to unrelated portions of the
  existing shared fixtures were removed rather than included in this change.
- Playwright desktop/mobile checks: **2 passed**. An initial rerun timed out
  during page navigation under concurrent test load; the final run used an
  explicit 180-second runner timeout and completed both tests. Codex mobile and
  OpenRouter desktop model-dialog screenshots were inspected; there is no
  horizontal overflow, and reasoning/mode controls remain inside the dialog.
- Alembic topology: **280 revisions, one head**,
  `20260930_020000_account_reasoning_policy`. The existing repaired timestamp
  collision warning remains; topology passes.
- Isolated database upgrade/check reports the new revision,
  `migration_policy=ok`, and `schema_drift=none`. Migration regression covers a
  historical account's empty-map backfill and downgrade/upgrade roundtrip.
- Strict change validation and strict main-spec validation passed.

## Baseline exception and qualification limits

`test_backend_responses_websocket_sanitizes_source_reasoning_for_native_upstream`
expects an empty reasoning item while the existing sanitizer preserves plaintext
as `summary_text`. The identical failure was reproduced in a pristine detached
worktree at `4586ad7a6`; its behavior was not changed by this feature. The broad
transport run excludes this single pre-existing failure, not the surrounding
transport suite.

Tests use local upstream stubs and synthetic account/catalog data. They establish
routing, wire preservation, persistence, UI and cleanup contracts; they do not
establish live OAuth acceptance or every provider's current model entitlement.
No complete-repository test-suite or cloud PR-gate success is claimed.

## Coherence and operational notes

Existing accounts remain unrestricted after the migration. There is no new
environment setting or inferred plan capacity. Account eligibility is not a
payload-rewriting rule, and ownership is not transferred to escape a restriction.
A non-owned incompatible warm lane can fork while retaining the old lane for
requests still eligible on its account. Strict owned requests fail explicitly.
Client-side Ultra cannot be separately routed when the client sends Max.

No unresolved feature-specific correctness issue was found. The change is ready
for archive confirmation; it remains active until the operator confirms.
