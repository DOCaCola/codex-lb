# Design

## Context

Production conversation 01a0f74e-240c-7823-be4b-104babb36b11 failed at 2026-10-01T12:42:26Z on an undeclared tool after delivering an assistant progress message. A reconnect at 12:42:27Z received Anthropic's assistant-prefill refusal. Responses projection currently preserves assistant tails but does not supply a user continuation. Source settlement records forwarding exceptions and rethrows them; native Messages already has an outer error serializer, translated Responses does not.

## Goals / Non-Goals

Preserve history, tool-pair validation, signed-state ownership and exactly-once settlement. Support Codex retries without a client fork. Do not delete assistant content, fabricate missing tool results, infer undeclared tool aliases, retry generation after output, or rewrite native Messages. No production changes.

## Decisions

- Append a single user text block `(continue)` in `project_responses` after search/pending-call validation when the final projected role is assistant. This is an explicit upstream projection rule for translated Responses/Chat, not a hidden request retry. User endings and summarization requests already ending in user instructions need no extra turn. Keep logical replay untouched so synthetic input never accumulates or changes strict-owner classification.
- Preserve the pending-call rejection before this transformation. Signed thinking/search blocks remain unchanged and subject to prior authentication/ownership checks; the continuation marker does not authorize migration or supply tool results.
- Serialize `ModelSourceForwardingError` outside the settlement generator in the shared source Responses response composition. The attempt closes/releases/logs with its original cause before the client receives one `error` event. Both HTTP and the in-process WebSocket bridge consume that event. Do not catch cancellation or ordinary programming errors. Native Messages and Chat keep their existing protocol serializers.
- Reject undeclared tools without alias inference. Log source/model/response identity, content index, declaration count, a SHA-256 name fingerprint and a bounded syntactically safe name. Malformed/oversized names are fingerprint-only; do not log input arguments, call identifiers, history or credentials.

## Risks / Trade-offs

The continuation adds an instruction to assistant-tail translated requests; this is preferable to deleting progress or signed context. It does not guarantee upstream success for malformed signed tool history. Unknown tool refusals remain real errors, but no longer abruptly close the WebSocket and their safe name becomes diagnosable.

## Reference evidence

Inspected October 1, 2026: OpenCodex 8a005dd98ff12cdc000c6f4961cbf71a592d6b6b, `src/adapters/anthropic.ts` lines 852–860 appends `(continue)` for assistant tails. CLIProxyAPI d33f63f8e3d98428440ebca5a5b6a981a61ff71e, `internal/translator/claude/openai/responses/claude_openai-responses_request.go` drops unsupported trailing assistant prefill; commit 6f25b9a1 introduced the Opus 5/Sonnet 4.6 rule on August 29, 2026. This implementation adapts the history-preserving behavior, not the deletion policy. No third-party code is copied.

## Migration Plan

No data migration or configuration required. Normal deployment after verification; rollback restores previous projection/error delivery. No live history edits are needed.
