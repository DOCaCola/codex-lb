# Design

## Context

`request_kind` drives warmup exclusions, token-count cost coverage and durable rollups. It is not an ingress API operation. Control requests currently discard their route classification on logging.

## Goals / Non-Goals

Identify existing logged requests using the existing model-cell secondary line. Do not add rows for embedded tool events, poll logging, inferred prices or new table columns.

## Decisions

- Add nullable `request_operation` metadata. Existing rows remain unknown; do not infer ingress from model names.
- Bind a typed operation to HTTP/WebSocket ingress using server method and canonical route, never client headers or request content. Pure ASGI scope ownership keeps context through response streams and resets it on completion.
- Snapshot the operation at persistence handoff and on bridge/WebSocket turn state so reusable upstream workers cannot attribute a new request to the first connection's route. Model-source dispatch owns a snapshot too.
- Internal warmup/automation producers explicitly report their known upstream operation: Responses for quota/limit warmup and automations, Compaction for the compact-based proxy warmup. Workload kind and accounting remain unchanged.
- Image adapters keep ingress image operations even when their upstream uses Responses. Standalone search has its own label; a search tool inside Responses does not.
- Frontend uses shared localized operation labels beneath Model and in details, with workload suffixes such as Warmup. Unknown retained operations remain Unknown.

## Risks / Trade-offs

No historical reconstruction is attempted. Classification is observability only; it must not change settlement, routing or privacy redaction. Native realtime labels must not expose call IDs. No operation-specific aggregates or filters in this change.

## Migration Plan

Add nullable metadata after the current head. Verify populated upgrade/downgrade and schema drift. No production deployment in this task.
