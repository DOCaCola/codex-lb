# Integrate upstream main
## Why
Upstream chart fixes overlap the fork's shared provider charts. Published upstream
and fork migration convergence revisions also require a new common head.
## What Changes
- Preserve provider chart gaps while applying upstream Codex observation alignment.
- Join published migration histories without rewriting either parent.
## Capabilities
### Modified Capabilities
- provider-account-trends: preserve provider-specific observation semantics.
- database-migrations: converge upstream and fork heads.
## Impact
Chart adapter, regression tests, additive no-op Alembic merge.
