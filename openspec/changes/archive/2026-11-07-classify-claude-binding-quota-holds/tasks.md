## Implementation
- [x] Classify overlapping quota and transient holds by their binding horizon.
- [x] Separate quota reset evidence from retry deadlines.
- [x] Verify HTTP/WebSocket regressions, ownership and mixed pools.
- [x] Validate specifications and repository checks.

106 routing/quota tests and 191 adjacent failover/authentication/inference tests
passed sequentially. The parallel runs had replay-history mismatches (one in
the first group, five in the second); all passed in the sequential reruns.
Seven binding-hold regression cases also passed after the final constant reuse.
Ruff, repository checks and strict OpenSpec validation passed; ty retained its
12 existing diagnostics. No live upstream experiments or production changes.
