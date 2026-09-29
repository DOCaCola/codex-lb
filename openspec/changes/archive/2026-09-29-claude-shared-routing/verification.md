# Local verification

- Claude unit/integration regression suite: 466 passed.
- Focused scheduling/routing/settings API suite: 131 passed (overlaps above).
- Native/Responses cleanup and migration roundtrip suite: 97 passed (overlaps above).
- PostgreSQL routing/capacity suite: 31 passed in an isolated disposable database.
- SQLite and PostgreSQL: upgrade to head, migration policy and schema drift checks passed.
- SQLite migration: parent -> revision -> parent -> head roundtrip passed.
- Dashboard routing/settings tests: 65 passed.
- Browser routing-pool checks: desktop 1440px and mobile 390px passed;
  screenshots inspected, independent account controls fit both layouts.
- Frontend TypeScript check, changed-component ESLint and production build passed.
- Application typing and new scheduling/migration test typing passed.
- `make lint`, strict change validation and all 72 main specifications passed.

An unrestricted repository-wide `ty check` also inspected the tests and reported
425 diagnostics across test modules. That run is not a clean repository-wide
typing result; application-only and newly added typed checks above are clean.

No real upstream requests, production changes, commit, push or deployment.
The isolated PostgreSQL container was stopped and auto-removed after testing.
