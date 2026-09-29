## 1. Implementation
- [x] 1.1 Add typed metadata errors, Retry-After parsing and durable endpoint scheduling state.
- [x] 1.2 Coordinate manual/background refreshes with bounded claims and preserve concurrent state.
## 2. Verification and documentation
- [x] 2.1 Add route and concurrency regressions; run Claude suites and lint/type checks.
- [x] 2.2 Sync Claude specs/context and user documentation.
## Delivery runbook
After verification, commit and push to fork main. Deploy with the existing production upgrade script and verify readiness and revision; no new deployment scripts or configuration are required.
