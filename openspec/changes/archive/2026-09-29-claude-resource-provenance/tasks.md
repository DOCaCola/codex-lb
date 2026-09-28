## Implementation
- [x] 1. Resource contract, SQL storage and migration.
- [x] 2. Native resolution and persist-before-delivery integration.
- [x] 3. Regression/migration verification and main spec sync.

Verification: broader Claude/source-WebSocket suite 449 passed; added nested-file
regression and final focused resource tests also passed. PostgreSQL ownership
suite 15 passed, then final resource suite 8 passed. SQLite and PostgreSQL fresh
upgrade/schema checks and migration downgrade/upgrade passed. make lint, scoped
ty, strict change validation and all 72 main specs passed. PostgreSQL test fixture
recreates tables without migration stamps, so migration roundtrip used a separate
fresh isolated database. No live OAuth qualification, commit or deployment.
