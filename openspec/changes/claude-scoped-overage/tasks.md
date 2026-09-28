## Implementation
- [x] Scoped classification and atomic persistence.
- [x] HTTP, native JSON/count_tokens and WebSocket regressions.
- [x] Mixed-deadline persistence/selection and malformed-evidence tests.
- [x] Sync specs and run validation.

Verification: broader Claude/source-dispatch suite 542 passed; final focused
classifier/failover run 67 passed including the additional model-window overshoot
case. Focused HTTP/WebSocket run 65 passed. Ruff, ty, whitespace checks, strict
change validation and all 72 main specs passed. One existing dependency deprecation
warning. No live OAuth or PostgreSQL qualification; no commit, archive or deployment.
