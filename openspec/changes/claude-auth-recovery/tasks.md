## Implementation
- [x] Capture credential snapshots and implement fenced forced refresh.
- [x] Integrate bounded authentication recovery and generation-specific backoff.
- [x] Test route recovery, concurrency, ownership and failure outcomes.
- [x] Validate Claude/shared dispatch suites, lint, typing and specs.

Verification: 391 Claude/shared-dispatch tests passed; Ruff, ty, strict change
validation and all 72 main specs passed. Tests cover future-expiry401, newer
generation reuse, concurrent claims, forced-refresh cancellation, terminal and
uncertain failures, repeated rejection, native JSON/count_tokens, HTTP/WS
Responses and strict thinking/search ownership. No live OAuth calls, schema
changes, commit, push or deployment.
