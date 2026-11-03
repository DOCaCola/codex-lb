## Implementation
- [x] Capture quota restrictions before fresh usage dispatch and reconcile confirmed headroom.
- [x] Verify manual/scheduled refresh, mixed restrictions, failure and concurrency behavior.
- [x] Validate specs and focused tests.

Validation: metadata suite 23 passed; adjacent reset, observation, pool, failover
and quota suites 105 passed; bound-owner upgrade recovery test 1 passed. Ruff,
targeted type checking, strict change validation and all 79 main specs passed.
