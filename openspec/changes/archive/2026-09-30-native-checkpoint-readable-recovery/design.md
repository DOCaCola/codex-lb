# Design

## Context

See proposal.md. The native compact service sees the full logical input before
wire-budget reduction and the successful returned ciphertext. Source preparation
currently rejects that ciphertext. Existing replay storage supplies atomic,
private, integrity-checked, bounded files with restart recovery and expiry.

## Goals / Non-Goals

Recover complete visible context for newly observed checkpoints. Do not decrypt
OpenAI state, retain every normal turn, silently shorten history, fabricate
summaries, or recover checkpoints that predate observation.

## Decisions

- Store a digest-addressed record in a separate checkpoint namespace, using the
  existing replay storage. Require an API key and a real conversation/session
  identity; do not share anonymous or generic fallback scopes.
- Capture only after successful compaction and usage settlement. Resolve earlier
  known checkpoints first. Unresolved handles, unknown semantic items, hosted
  resources or unpaired direct tool outputs make the record ineligible.
- Keep messages and attachments intact and tool call IDs paired. Remove telemetry,
  statuses and nonsemantic message IDs; omit local markers and tool advertisements.
  Convert visible reasoning to assistant text; do not retain provider ciphertext.
  Do not truncate tool output, discard old user turns or deduplicate repeated
  messages by their text. Preserve original instructions as developer context.
- Bind the checkpoint to the exact compact replacement prefix too, so a v1
  replacement that keeps original user messages does not duplicate them when
  expanded. Prefix removal requires the authenticated checkpoint and exact
  canonical equality with its recorded replacement; no heuristic overlap.
- Materialize before source policy and dispatch for HTTP, WS and source compact.
  Preserve native checkpoint wire behavior. Known recovery does not pretend to
  preserve hidden provider reasoning; it restores the complete visible input.
- Use existing defaults: 1 hour, 1000 records, 256 MiB per record, 1 GiB total.
  Eviction, corrupt files and cache misses remain explicit preparation failures.

## Risks / Trade-offs

- Large recovered history may exceed target capacity → return its capacity error,
  never retry with shortened input. Users can compact with the original provider
  or provide a readable handoff; no extra summary call is silently billed.
- Old checkpoints and native handle-only compacts cannot be reconstructed →
  preserve existing indexed error. New retention does not repair legacy entries.
- Sensitive readable context is retained → private permissions, scoped lookup,
  digest-only keys, bounded expiry and no content in diagnostics.

## Migration Plan

No schema/config changes. Only compacts observed by the new code seed recovery.
Rollback ignores the separate records; periodic cleanup expires them.

## Reference evidence (inspected 2026-09-30)

- Sub2API 42bc7f6c: encrypted compact sanitization removes items; merged #5084
  (2026-07-31) and #6397 (2026-09-05) do not reconstruct missing history.
- CLIProxyAPI 97f244b8: Claude translation warns/drops unsupported input; own
  Antigravity capsules decode only proxy state. #5516 is closed, not merged.
- OmniRoute dbe703a0: normal Responses-to-Chat rejects unsupported input;
  ChatGPT-web bridge decodes ocx1 and otherwise emits a placeholder.
- OpenCodex 569e3e7d: native ciphertext remains opaque; portable ocx1 summaries
  do not establish recovery of encrypted native history.

These are source/report observations, not independent live qualification.
