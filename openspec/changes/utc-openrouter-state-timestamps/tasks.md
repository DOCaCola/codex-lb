## 1. Implementation

- [x] 1.1 Require aware OpenRouter observation timestamps and write them as UTC
- [x] 1.2 Compare the catalog refresh schedule against aware UTC
- [x] 1.3 Migrate stored naive observation times to UTC, with a downgrade to naive UTC

## 2. Verification

- [x] 2.1 Migration test: naive values become UTC, the state validates, and downgrade and re-upgrade round-trip
- [x] 2.2 Unit and OpenRouter integration tests, migration topology, ruff, ty and strict OpenSpec validation
- [ ] 2.3 Archive after deployment
