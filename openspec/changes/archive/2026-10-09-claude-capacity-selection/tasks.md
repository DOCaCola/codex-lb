## Implementation
- [x] Add typed capacity reselection and preserve ownership constraints.
- [x] Expose account concurrency through API and dashboard.
- [x] Verify route, cleanup, settings and frontend regressions.
- [x] Sync specs and run validation.

Verification: 463 Claude/shared-dispatch tests passed; focused 13-test capacity
run also passed after adding reservation-count assertions. Nine frontend tests
and desktop/mobile Playwright checks passed. Screenshots inspected at 1440px and
390px. Python Ruff/format/ty, frontend typecheck/ESLint, diff checks, strict change
validation and all 72 specs passed. Existing test dependency deprecation warning
remains. Tests use local mocks, not live OAuth. No commit, push or deployment.
