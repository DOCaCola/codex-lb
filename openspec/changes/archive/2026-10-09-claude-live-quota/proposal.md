## Why
Inference response headers contain quota observations which currently never reach Claude routing or dashboard usage.

## What Changes
- Capture typed per-window quota observations for each physical response, fenced to its sending credential generation.
- Preserve separate poll freshness, merge concurrent settings/poll/header state safely and bound history sampling.
- Reuse existing quota display and eligibility without changing routing strategies or cooldown policy.

## Capabilities
### Modified Capabilities
- `claude-accounts`: passive inference quota observations.

## Impact
Claude transport, repository, polling and quota interpretation. Existing JSON state; no database migration or new network probes.
