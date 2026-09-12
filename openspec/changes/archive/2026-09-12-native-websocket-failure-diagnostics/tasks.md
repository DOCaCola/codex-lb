## Tasks
- [x] Add bounded failure-only native receive diagnostics and local queue provenance.
- [x] Test classification, correlation, deduplication, cancellation, and sensitive-data exclusion.
- [x] Validate tests, lint, typing, and specifications; archive verified change.

Verification: 147 native transport and WebSocket adapter tests passed, including actual message-queue overflow through the receive adapter. `make lint`, typing, strict change validation, and diff checks passed. No commit, push, or production deployment.
