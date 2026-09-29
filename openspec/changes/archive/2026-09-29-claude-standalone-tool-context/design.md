# Design

## Context

See proposal.md for motivation and the Claude account context for inspected reference revisions. The shared Responses projector runs after scoped previous_response_id expansion and signed-history authentication. It is also used by the Chat adapter; native Messages uses a separate path.

## Goals / Non-Goals

Preserve portable standalone output content without making it an executable tool cycle. Do not recover a missing explicit previous response, change retained-history lifetime, relax ownership, or synthesize signed thinking or missing tool results.

## Decisions

- Classify against all call identifiers in the expanded input plus the existing seen/pending sets. A forward reference is invalid ordering, not standalone context; an already consumed real result is a duplicate. A standalone output cannot interrupt unresolved calls. This keeps true tool-cycle invariants instead of implementing a catch-all error fallback.
- Lower true standalone output into a labeled user content block followed by the existing text/image conversion. Keep original item kind and call ID in the label so the semantic change is explicit to the model. Do not fabricate a tool_use as that would falsely claim execution provenance. Preserve each standalone item, including repeated contextual items, rather than discard data by call ID.
- Leave logical input untouched. Persisted continuation keeps the original standalone item, which is projected once on each outbound request; labels do not accumulate across turns. Missing explicit continuation state remains a hard error before projection.
- Keep rejection diagnostics in the projector, where classification and pending state are available. Log an existing request ID, index, kind, reason and bounded identifier hash only. Do not add full failed-request archives or success-per-item logging.

## Risks / Trade-offs

- Context lowering changes role semantics → mark standalone provenance explicitly; never use it to satisfy actual pending calls.
- A caller can omit a historical call without using previous_response_id → preserve its output only as context, not as an authenticated tool result or signed continuation.
- Anthropic may reject other history constraints → retain existing failures; do not introduce generation retries or fabricate results.
- The original production payload was not retained → local regression verifies the known incompatibility, not the exact unobserved failed input. New diagnostics distinguish future pairing failures without exposing history.

## Migration Plan

No settings or migration are required. Normal deployment applies the projector change; reverting the code restores the old rejection behavior without changing retained records. Commit, push and deployment are outside this implementation request. HTTP/WS mocks qualify protocol projection and cleanup; live OAuth acceptance remains separately testable after deployment.
