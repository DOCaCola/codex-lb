## Implementation
- [x] Collect completed HTTP output items with bounded per-attempt state.
- [x] Integrate terminal reconstruction without changing downstream events.
- [x] Test streamed custom-tool continuations, authoritative snapshots, limits, and lifecycle cleanup.
- [x] Validate and synchronize specifications.

Validation: 1611 relevant unit/integration tests passed; Ruff, production typing, architecture, timing seams, cancellation safety, strict change validation, and all 58 main specifications passed. Production was not modified.
