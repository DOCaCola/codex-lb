## Context
Production on 2026-09-29 rejected input item 38 with `invalid_call_id`, no string identifier and no pending calls. Failed content was not retained, so complete metadata cannot be confirmed retrospectively. Current Codex `ResponseItem::FunctionCallOutput` permits an optional call ID. OpenCodex #3807 was resolved by recognizing complete external-task envelopes, including established-history occurrences.

## Decisions
- Share a pure external-task classifier between projection and signed-history replay. Require function_call_output, absent/null/blank-string pairing key, nonblank string id/name/namespace, and nonblank supported text/image content. Wrong-typed identifiers remain malformed. Validate the entire content array; never preserve a partial task by dropping unknown blocks.
- Project canonical tasks as ordinary user content with existing Claude text/image validation, not labeled orphan results or fabricated tool calls. Keep original logical items for replay. A task is a new user turn for completed thinking, but cannot interrupt any pending tool call. Search resources remain strictly account-bound and all opaque state is authenticated before any omission.
- Preserve existing nonempty-ID standalone-context behavior and strict paired-call semantics. Explicit missing previous_response_id state remains an error before projection.
- Rejection logs add only call-ID type/presence and metadata completeness to existing bounded diagnostics; no raw IDs, text, image data or success-per-item logging.

## References
Inspected 2026-09-29: OpenCodex 8a005dd98 (task-input.ts; issues #3735/#3807, merged #4058); CLIProxyAPI d33f63f8 (broader standalone-output-to-user conversion); Sub2API 9a62841fd (drops orphan tool_results); OmniRoute 113de57b (filters orphan results on Responses-to-Chat). Adopt explicit task classification, not heuristic FIFO pairing or data deletion. No third-party source is copied.

## Verification / Qualification
Unit tests cover complete and malformed shapes, text/image order, logical immutability, active tool cycles and signed replay boundaries. Public HTTP/WS tests cover initial and established-history tasks and retained genuine tool continuation. Mocks qualify protocol behavior only, not live OAuth acceptance or the exact unrecorded production envelope. No live traffic is altered by this work.
