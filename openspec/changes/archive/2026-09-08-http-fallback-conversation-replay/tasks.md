## Implementation
- [x] Add bounded, expiring replay storage with scope isolation and atomic publication.
- [x] Integrate completion retention, request expansion, and ephemeral owner recovery.
- [x] Cover incremental turns, full resends, restarts, expiry, corruption, limits, and isolation.
- [x] Validate code and specifications; synchronize and archive the verified change.

Validation: 1584 relevant runtime tests plus 3 heartbeat-maintenance tests passed; Ruff, production-code type checks, cancellation safety, architecture, timing seams, 58 main specs, and strict change validation passed.
