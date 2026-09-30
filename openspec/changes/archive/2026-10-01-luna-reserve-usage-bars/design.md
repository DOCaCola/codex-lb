# Design

## Context

Spark already has additional-quota bars and a routing-oriented history repository. Reserve is conditional account telemetry, not a universally available model. See proposal.md.

## Goals / Non-Goals

Show the latest upstream Reserve usage in the same visual layout. No graph, model catalog, fallback, entitlement grant or routing policy is introduced.

## Decisions

- Extend the usage client with an explicit capability argument, default false; only account usage refresh opts in. All egress transports share the built headers, including the 401 retry.
- Retain a typed, timestamped Reserve snapshot in a nullable account JSON column. This is current metadata, not a history table. It avoids putting conditional/no-window observations in Spark's numeric, routing-oriented history. Missing observations replace the current snapshot rather than invent percentages. Old history is not needed for this bar-only scope.
- Bind writes to the credential ciphertext observed for the query and reject conflicting account/user echoes. Re-import clears this snapshot so a replaced account cannot inherit it.
- Append the Reserve snapshot as an additional-quota presentation entry, without adding it to the routing registry. Use existing freshness policy; stale observations have no current windows.
- Preserve `metered_feature` as required by Codex's generated upstream parser. Minimal OpenCodex eligibility fixtures are not evidence for relaxing the complete usage schema.

## Risks / Trade-offs

The capability header explicitly advertises Reserve support in the usage contract. Here it is used solely for operator telemetry; it does not enable inference. Live account coverage remains unqualified until an actual Reserve-bearing response is available. Tests establish parsing and display, not entitlement.

## Migration Plan

Add one nullable JSON column after the current Alembic head; existing accounts start without Reserve telemetry and populate on refresh. Downgrade removes only that metadata. No production upgrade in this task.

## References

- OpenAI Codex `60947e234156ac12bdb7fba2477d3965f166bd34`: backend-client/src/client/rate_limit_resets.rs, backend-client/src/client.rs, tui/src/chatwidget/tests/luna_reserve_usage_tests.rs.
- OpenCodex `cae9b553e9b882dd13781a7f3ee6f68c0dcc8c4f`: src/codex/reserve-availability.ts. Its strict grant is distinct from these display observations.
