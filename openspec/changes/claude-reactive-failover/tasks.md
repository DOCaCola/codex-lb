## Implementation
- [x] Implement refusal classification and persistent scoped cooldowns.
- [x] Integrate bounded native and translated request rebuilding.
- [x] Verify settlement, cancellation, ownership and budgets with regressions.
- [x] Validate migration, lint, typing, tests and specs.

Validation: 224 Claude tests; shared dispatch suite 145 passed plus its renamed
attempt-boundary assertion corrected and rerun. Fresh isolated database upgrade
and check: migration_policy=ok, schema_drift=none. Claude migration downgrade /
upgrade covered by integration tests. Topology checked against local main (no
remote configured in this checkout). Ruff and ty pass; strict change validation
and 72 main specs pass. No live OAuth testing, commit, push or deployment.
