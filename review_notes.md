# Review notes: Claude accounting, observability & reasoning (uncommitted)

## Resolution pass (2026-09-29)

| Item | Outcome |
|------|---------|
| A | **Fixed.** `aggregate_by_bucket`, `_aggregate_activity`, `aggregate_usage_metrics_since` and fleet pressure metrics use `request_cost_expressions`, so raw tails match the folds (rollup parity tests pass with coverage counts). `BucketModelAggregate`/`RequestActivityAggregate` now hold cost only in `cost_coverage` (duplicate `cost_usd` removed). `costCoverage` added to dashboard `summary.cost`, `comparison.previous`, cost trend points, `/api/usage/summary` and fleet windows; `RequestCostCoverage` moved to `modules/shared/schemas.py`. Dead `_cost_summary_from_logs` path removed. Dashboard cost card shows the incomplete label and withholds average/comparison. |
| B | **Fixed + verified.** `formatCoveredCost` renders `$X known · coverage unavailable`; `Unknown` only when no known cost. New test `test_upgrade_repair_restores_coverage_only_for_retained_buckets` shows the hourly repair clears `coverage_unknown` for retained buckets and keeps pruned ones unknown. Report and lifetime repairs were read, not newly tested. |
| C | **Fixed.** Clamp restored; regression test added. |
| D | **Fixed.** Absent `thinking` stores NULL (the default is adaptive on Opus 5/5.5, Sonnet 5/5.5 and Fable; off on Opus 4.x and Haiku), so `disabled` is the one spelling for "off". |
| E | **Decided: not inferred.** The effort default depends on the model (`medium` on Opus 5.5, `high` elsewhere), so NULL means "left to the API default". Spec delta, design and `docs/claude-accounts.md` updated. |
| F | Null sampling fields are dropped in `project_responses` (defensive only: `/v1/responses` and Chat already strip nulls). `top_p` left strict. Claude catalog-only pricing **kept as intended**: Claude source rows are read-only projections of the same catalog, so there's no operator override to honor. Reference comparison and the clarified wording are in design.md. |

Tests (final tree): frontend typecheck/lint clean, vitest 1735/1738 (3 failures predate this work: ko/zh-CN i18n parity, MSW handler coverage; 3 formatting tests need an `en_US` locale). Backend full run: 57 failed / 14690 passed, the same set as the pre-change baseline minus the fixed harness test. These failures cover areas the uncommitted work touches (migrations, model-source headers, reports/request-log service fixtures, source-cost settlement) and are **still undiagnosed**.

Reviewed 2026-09-29 against the uncommitted working tree on top of `ae8d1aee6` (97 modified/new files).
Static review only: PyPI/npm were blocked in the review sandbox, so **no tests were run**.
The earlier 195-test targeted run predates later edits (e.g. `app/core/usage/coverage.py`).

## First step

```bash
uv run pytest -q tests/unit tests/integration
cd frontend && bun run typecheck && bun run lint && bun run test
```

## Status of the original five review findings

| # | Finding | Status |
|---|---------|--------|
| 1 | LiteLLM 1h cache-write key (`cache_creation_input_token_cost_1h`) | **Fixed.** `pricing_catalog.py` `parse_litellm` now reads `cache_creation_input_token_cost_above_1hr`; long-context uses `cache_creation_input_token_cost_above_1hr_above_{N}k_tokens`. Tested in `tests/unit/test_pricing_catalog.py`. *Unverified:* that the long-context 1h key name exists in the live LiteLLM feed (couldn't fetch it). |
| 2 | Long-context tier ignored for Claude source costs | **Fixed.** `model_sources/catalog.py::source_model_cost_usd` routes `source.kind == "claude"` through `calculate_claude_cost_breakdown` (tier-aware, incl. cache writes). |
| 3 | Budget thinking forwarded with incompatible sampling | **Fixed.** `claude/protocol.py` (~line 357) rejects `temperature != 1` and any `top_p` when `thinking` is set. |
| 4 | Native `output_config.effort` / effective effort missing | **Mostly fixed.** `proxy/api.py` (~5705–5730) reads native `output_config.effort`; persists `upstream_reasoning_effort`, `upstream_thinking_mode`, `upstream_thinking_budget_tokens` (migration `20260929_040000_claude_usage_detail`). |
| 5 | Claude cost hiding keyed on model name | **Fixed.** `core/usage/logs.py` and `core/usage/coverage.py` key on `model_source_kind == "claude"` + new `cost_provenance`; dispatch sets `api_equivalent_estimate` / `unpriced`. Genuine $0 rows from other providers are preserved. |

## Open items (fix before committing)

### A. Cost aggregates that still bypass coverage (main gap)
These still `func.sum(RequestLog.cost_usd)` with no priced/unpriced/unmetered counts and no legacy-Claude-zero exclusion, so dashboard views can present incomplete cost as complete:

- `app/modules/request_logs/repository.py::aggregate_by_bucket` (~603) -> dashboard overview trends
- `app/modules/request_logs/repository.py::_aggregate_activity` (~750)
- `app/modules/request_logs/repository.py::aggregate_usage_metrics_since` (~849) -> usage summary / 7d cost by model (`cost_count` counts legacy Claude $0 rows as priced)
- `app/modules/usage/builders.py` (`build_trends_from_buckets`, `build_usage_cost_from_aggregate`, `_cost_summary_from_logs`) -> carry `CostCoverage` through and expose it
- `app/modules/fleet/observability.py:151`

Fix: use `request_cost_expressions(RequestLog)` from `app/core/usage/coverage.py` (same filters/attempt boundaries as the sum), add `costCoverage` to the response schemas, and render with `formatCoveredCost` on the dashboard cost card / trend chart.

### B. Historical rollups collapse to "Unknown"
The migration sets `coverage_unknown = 1` on every existing rollup row while `priced_requests` defaults to 0. `frontend/src/features/dashboard/cost-coverage.ts:20` returns `"Unknown"` whenever `priced == 0 && unknown`, hiding a known historical dollar sum, and doing so permanently for buckets whose raw rows were pruned.
- Render `$X known · coverage unavailable` when `coverageUnknown && knownCost > 0`, reserving `Unknown` for "no known cost at all".
- Verify the repair fold (`reports_coverage_repair_from`, `upgrade_repair_from`, `coverage_repair_attempted`) clears `coverage_unknown` for buckets whose raw rows still exist; add a test for it.

### C. Negative cost possible for non-Claude sources
`app/modules/model_sources/catalog.py:293`: `billable_input = input_tokens - cached_input_tokens` dropped its former `max(0, ...)`. If a provider reports cached > input, cost goes negative. Restore the clamp (or return `None` for inconsistent usage).

### D. Thinking-mode naming
`app/modules/proxy/api.py:5730` stores `upstream_thinking_mode = "omitted"` when no `thinking` block is sent. This collides with Anthropic's `thinking.display = "omitted"`, and a native `{"type": "disabled"}` is stored as `"disabled"`, so "off" has two spellings. Use one value (e.g. `"disabled"`) for both, or `NULL` for absent.

### E. Effective adaptive effort not recorded
Adaptive thinking without an explicit `output_config.effort` stores `upstream_reasoning_effort = NULL`. If the goal is *effective* effort, record the API default (confirm current default in Anthropic docs) or add a flag that it was defaulted.

### F. Minor
- `claude/protocol.py` ~357: explicit `temperature: null` with thinking is rejected (and would be forwarded as `null` without thinking). Drop null sampling fields instead.
- `top_p` is rejected entirely with thinking; Anthropic permits 0.95–1. Strict but safe, so it's fine to leave.
- Claude source pricing now ignores the source entry's own `input_per_1m`/`output_per_1m` and always uses the global catalog. Confirm that's intended and documented.

## Intentionally out of scope
Budget enforcement (`app/modules/quota_planner/repository.py` 310/483/688) still sums raw `cost_usd`. Per the design discussion, strict hard-dollar-cap behavior with unpriced usage (OmniRoute-style fail-closed) should be an explicit policy decision, not implied by reporting subtotals.
