# Design

## Context

See proposal.md. Middleware supplies a method/path operation; source dispatch and bridge state snapshot it. The existing terminal-trigger validator identifies compaction but discards its boolean result.

## Goals / Non-Goals

Goals: reuse that result, isolate websocket turns and nested handoff, and classify actual internal compact calls.
Non-goals: new parsing, log producers, accounting changes, history backfill or deployment.

## Decisions

- Return the existing validator result and refine only Responses. This preserves image and handoff labels without rescanning solely for logging.
- Refine HTTP context before dispatch; refine websocket request state without mutating connection context.
- Scope handoff operation with a reset-on-exit context manager. Explicit compact-service logging reflects actual execution even for internal callers.
- Extend the existing enum/localized secondary label; no migration is necessary.

## Risks / Trade-offs

- Context leaks → restoration on cancellation/error plus concurrent and nested tests.
- Adapter marker removal → snapshot before conversion.
- Workload drift → leave request_kind and settlement unchanged.

## Migration Plan

Normal application update; no data migration. Historical rows remain unchanged. No deployment is authorized by this change.
