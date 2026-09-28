## Implementation
- [x] Implement classification and cancellable same-account retry.
- [x] Add bounded SSE startup inspection.
- [x] Test recovery, no-replay boundaries and resource cleanup.
- [x] Validate suites, lint, typing and specs.

Verification: 442 Claude/shared-dispatch tests passed; the final startup-parser
refinement and two additional malformed-event cases passed in the focused
44-test overload run. Ruff, formatting, ty, diff checks, strict change validation
and all 72 main specs passed. No live OAuth traffic tested; not deployed.
