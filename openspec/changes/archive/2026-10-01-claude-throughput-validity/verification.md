# Verification: Claude throughput validity

Verified October 1, 2026. Local implementation only; no commit, archive, push or production deployment.

## Summary

| Dimension | Result |
| --- | --- |
| Completeness | 4/4 tasks complete; all 5 changed requirements implemented |
| Correctness | Regression coverage for each changed requirement and scenario |
| Coherence | Shared backend calculation, matching frontend policy, existing layout preserved |

No critical issues or implementation/spec divergences found. Main specs and capability context are synchronized. Ready for archive when requested.

## Implementation and scenario mapping

- Claude request usage and timing: `app/modules/model_sources/forwarding.py` observes nonempty redacted-thinking data, thinking-block signatures and signature deltas. `tests/unit/test_claude_accounting.py` covers opaque output and empty/metadata/terminal exclusions. Six deterministic public-route tests in `tests/integration/test_claude_inference.py` cover native Messages, Chat Completions and Responses: upstream opaque output at 1000 ms establishes TTFT before visible text at 3000 ms, with completion at 4000 ms. Output usage is retained and reasoning usage remains unknown.
- Estimated Claude throughput validity: `app/core/usage/throughput.py` and `frontend/src/features/dashboard/generation-speed.ts` implement inclusive output, successful status, nonnegative known TTFT and an inclusive 1000 ms minimum. Repository and frontend tests cover the exact production burst, 999/1000 ms boundaries, known/unknown reasoning and invalid/unsuccessful samples.
- Dashboard generation speed: request-table/detail tests and light/dark Playwright tests verify unavailable burst TPS, estimated valid Claude TPS and unchanged native output-minus-reasoning TPS.
- Reports daily speed trends: `app/modules/reports/repository.py` uses the shared expression; repository tests verify medians and eligibility for Claude and OpenRouter. Report chart/page tests verify the estimate explanation without new chart layout.
- Shared timing anchor: existing native attempt observation precedes Responses conversion. Public-route clock tests verify shared TTFT/duration anchors and unchanged token accounting. No timing clamp or stored-history backfill is introduced.
- Conversation analytics: `app/modules/request_logs/observability.py` uses the shared expression while retaining its existing successful-generation cohort. API tests verify excluded burst samples retain request, token, cache and TTFT observations; the conversation dialog explains gateway estimates.

## Executed checks

- Backend regression group: **292 passed**, covering Claude accounting, Reports repository/API, provider observability, Claude inference/Chat Completions and conversations API. One existing Starlette/AnyIO deprecation warning.
- Separate OpenRouter timing/model-source forwarding regressions: **148 passed**.
- Frontend request table, conversation dialog, TPS chart and Reports page: **129 passed across 4 files**.
- Production frontend build: passed, output confined to `/tmp/claude-throughput-browser.yixqC3/build`.
- Built-app Playwright: **2 passed** (light and dark). Table/detail screenshots inspected; no page errors. Screenshots are temporary local artifacts under `/tmp/claude-throughput-browser.yixqC3/results`, not new published documentation assets.
- TypeScript build check and ESLint on changed frontend files: passed.
- Ruff on changed Python implementation/tests: passed.
- Strict OpenSpec change validation and all main specs: passed; existing informational long-requirement notices remain.
- Diff whitespace validation: passed.

## Qualification limits and scope

The gateway cannot reconstruct hidden upstream generation time or distinguish upstream buffering from delayed opaque thinking for the reported production request. The one-second minimum excludes unstable observations; longer-window values remain gateway estimates, not proven model decode speed. No end-to-end substitute, fabricated reasoning count, cost change or native OpenAI policy change is introduced.

Concurrent unrelated Claude owner/quota recovery edits in this shared worktree were preserved and are not part of this change. Regression results describe the shared tree at execution time. Production remains unchanged.
