## Decisions
Use the existing settled source-dispatch boundary for account rotation. Each retry reparses original logical history and credentials. A request-wide budget allows four physical inference sends including signature recovery. Only explicit upstream HTTP 429 before stream ownership is established qualifies. Entitlement refusals remain caller errors without cooldown. Unified rejected-window headers create account cooldown; ordinary limits create model cooldown. Persist deadlines independently of quota polling using monotonic upserts.

## References
OpenCodex bounded rebuild/reselect; CLIProxyAPI failure scope; Sub2API cancellation and settlement. See workspace-local claude-429-failover.tmp.md for inspected revisions.

## Non-goals
Changing models, silently downgrading fast mode, retrying failures after stream delivery, claiming opaque resource portability.
