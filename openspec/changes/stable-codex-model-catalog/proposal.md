# Stable Codex model catalog

When an account ran out of quota, the next model-registry refresh dropped its
plan from the catalog, and the catalog came back when the quota reset. Codex
renders the catalog into its subagent tool description, so both flips rewrote
every client's tool definitions and broke prompt caches. On Claude the break
also discarded replayed thinking for hours.

## Scope

Base catalog membership on pool membership (deactivated or deleted accounts
leave), never on quota, rate limits, pauses or pending re-authentication, and
serve the catalog in a fixed order. Routing eligibility is unchanged: the load
balancer still excludes unavailable accounts per request.
