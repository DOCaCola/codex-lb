# Upstream integration verification

Integrated upstream main through f8ffbac2099a113fba54dfd8d77774f5bca80ffa
(20 commits). Three conflict files resolved by combining contracts rather than
discarding the shared provider chart or upstream Codex observation fixes.

- Affected backend selection/files/quota/settings tests: 723 passed, 9
  PostgreSQL-only tests skipped on SQLite.
- WebSocket/shutdown/dashboard/CI tests: 267 passed, 10 opt-in PostgreSQL
  migration-benchmark tests skipped.
- PostgreSQL usage and dashboard-user tests: 71 passed, 7 SQLite-only skips.
- New migration convergence: 3 tests passed from empty, upstream and fork heads;
  explicit-parent downgrade and re-upgrade preserve schema and both stamps.
- Existing Claude routing migration roundtrip: passed.
- PostgreSQL deployed-fork -> merged-head upgrade: passed; no schema drift.
- Frontend account/provider tests: 57 passed.
- Frontend typing, changed-chart ESLint, production build: passed.
- Application typing and make lint: passed. One Alembic head; published
  historical timestamp collision remains explicitly repaired and warned.
- Strict change validation and 73 main specs: passed.

GitHub confirms upstream PR2496 is merged at the fetched commit with successful
CI Required. This local fork integration is not a new upstream PR or claim of
cloud validation of the combined fork. Fork GitHub Actions remains disabled.
No push, deployment or production changes are included.
