# Verification — 2026-09-29

## Completeness and correctness

All six tasks complete; three added requirements synced to the main Claude spec.

| Requirement | Implementation | Regression evidence |
| --- | --- | --- |
| Automatic token capabilities | model_limits.py, CatalogModel, service projection, protocol/dispatch, model-selection UI, forward migration | Catalog discovery/unknown/obsolete-field tests; public Codex catalog and native/Responses request tests; seeded migration upgrade/downgrade/re-upgrade and schema drift |
| Account presentation parity | Shared quota-display, routing-policy, account-info-panel and pause button; Claude list/card/detail consumers | Claude/Codex component tests; read-only, quota preferences, unknown/stale/overshoot, routing PATCH payload; Playwright desktop/mobile and dashboard table |
| Account routing preference | Claude routing_policy column/API, shared scheduling Candidate | Four strategy preference tests; hard-owner and eligible-affinity integration tests |

## Executed checks

- Full Claude backend slice: 491 passed.
- Model-source catalog/projection/service/routing plus migration slice: 173 passed.
- Final targeted catalog/account API/migration run after added assertions: 31 passed.
- Frontend Claude/shared account/dashboard component slice: 178 passed across 19 files.
- Three Playwright browser scenarios passed (desktop/mobile detail, reconnect,
  reset confirmation, automatic model limits and dashboard). Final main scenario
  rerun also passed with the dashboard table assertion.
- Desktop/mobile screenshots inspected; no horizontal overflow. Captures are
  generated under frontend/test-results, not published production data.
- Frontend TypeScript, changed-area ESLint and production build passed.
- make lint passed: Ruff plus architectural and single-head migration checks.
- Scoped Python type check passed for changed application code, migration and
  new catalog/account/routing tests. Repository-wide ty reports 424 diagnostics,
  all under tests; no application diagnostics. Existing inference-test typing
  errors remain outside the edited portions, so the full type gate is not green.
- Strict change validation passed; all 73 main specifications passed.
- git diff --check passed.

## Coherence and limits

No critical implementation/spec mismatch found. Discovery takes precedence;
known metadata supplements absent fields, not generic guessed limits. Unknown
limits remain unavailable. Full capacity, client compaction hints and default
output budget are distinct. Existing global context-window policy is unchanged.

The old OpenRouter chooser test selector was updated to its existing provider
fieldset/API-key action; the chooser itself was not changed.

SQLite migration/data behavior is tested; PostgreSQL runtime qualification was
not performed. Mock inference establishes budget forwarding and ownership
invariants, not live model quality, OAuth entitlement or long-output reliability.
The only live evidence used here was the earlier read-only model discovery.

No commit, push, production deployment or credential mutation performed.
Ready for archive with the noted repository-wide type-check qualification.
