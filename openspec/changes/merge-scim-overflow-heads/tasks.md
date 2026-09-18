## Implementation
- [x] Add merge revision and graph-aware timestamp validation with tests.
- [x] Verify populated SQLite upgrade paths and downgrade behavior.
- [x] Run lint, types, SQLite migration and SCIM tests; sync specifications.
- [x] Verify PostgreSQL migration and SCIM tests (104 passed); verify PostgreSQL schema downgrade and re-upgrade without drift.
## Deployment
- [x] Commit and push using DOCa Cola identity (`23661e102`).
- [x] Back up production database, deploy through upgrade.sh and verify readiness and revision (`23661e102`).
