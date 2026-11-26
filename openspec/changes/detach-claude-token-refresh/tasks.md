## 1. Implementation

- [x] 1.1 Run the claim, refresh and settlement in a detached task with its own session, keyed by account and generation
- [x] 1.2 Let callers in the same process share the in-flight refresh

## 2. Verification

- [x] 2.1 Regression tests: a cancelled caller's refresh still settles; concurrent callers share one refresh; another worker's intent is never stolen; a refresh cancelled by shutdown keeps its intent (fail without the fix where behaviour changed)
- [x] 2.2 Unit suite, Claude integration tests, ruff, ty and strict OpenSpec validation
- [ ] 2.3 Archive after deployment
