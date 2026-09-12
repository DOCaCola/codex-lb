## Context
The unary control service owns native image request logging, while the route owns quota settlement. Previously only the route parsed usage. See proposal.md.

## Decisions
A typed per-request accounting record carries the public model and one parsed usage snapshot. The service captures it before invoking settlement and uses it in its existing request-log finalizer. The route consumes the same snapshot for settlement and cancellation cleanup. This avoids duplicate parsing of large image responses and avoids importing route dependencies into the service. Existing pricing computes costs from persisted tokens; no new pricing logic or fabricated usage is introduced.

## Risks and verification
Tests must exercise actual native routes and persisted request-log API costs with both limited and unlimited keys, and preserve cancellation/error cleanup. Missing or malformed usage remains unavailable. Success bytes and metadata remain untouched. No historical backfill can be inferred from logs lacking usage.
