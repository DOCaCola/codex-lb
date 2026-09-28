## Implementation
- [x] Typed header parsing, attribution and persistence.
- [x] Concurrency-safe poll/settings merge and per-window freshness.
- [x] Physical-response transport observation and bounded cleanup.
- [x] Regression tests, spec sync and validation.

Verification: broader Claude/source-dispatch suite 489 passed; final focused
observation/WebSocket run 63 passed (including seven additional reset/timeout
cases). Frontend Claude tests 10 passed, TypeScript and targeted ESLint passed.
Ruff, ty, diff whitespace checks, strict change validation and all 72 main specs
passed. No live OAuth or PostgreSQL qualification, commit, archive or deployment.
