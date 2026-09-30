# Design

## Context

See proposal.md. Shared source shaping calls the compaction guard after retained
continuation expansion and before Claude preparation. The current guard treats
all three compaction item types as opaque, including local markers whose summary
is an independent ordinary message.

## Goals / Non-Goals

Classify genuine marker-only state without changing native serialization,
retained logical input or visible context. Do not decode OpenAI checkpoints,
invent replacement summaries, repair live history or introduce hidden inference.

## Decisions

- Only context_compaction with missing/null encrypted_content and recognized
  marker metadata (type, id, internal_chat_message_metadata_passthrough) is
  payload-free. Empty strings, wrong-typed ciphertext and unknown payload fields
  remain explicit errors; omission must not hide future data-bearing formats.
- Reuse the common source projection for HTTP/WS, continued replay and source
  summarization. Native OpenAI shaping remains unchanged. Validate the entire
  projected list before replacing input; a later rejection must not publish a
  partially lowered input.
- Retained history expansion occurs first and keeps the original logical marker
  and summary. Only the source wire projection excludes markers. Keep all messages,
  tools, images and readable summaries in their existing order.
- Rejection diagnostics expose request ID, original item index, known subtype,
  ciphertext presence and a bounded classification reason, never values, lengths,
  IDs or content. Successful marker projection emits one aggregate count.

## Evidence (2026-09-30)

OpenAI Codex `ed0cc1a4ab30e1e83f1214e7a368c55b83fd089d`, protocol/models.rs:
ContextCompaction has optional id, encrypted_content and internal metadata.
OpenCodex `569e3e7dae48bafc54b8a1a7e3a85129befe2d98`, responses/parser.ts:
payload-free local markers are omitted because their plain summary is a separate
user message. Its fallback note for unreadable native checkpoints is not adopted.
Production's 2026-09-30T16:53:37Z rejection does not identify subtype or body, so
this implementation does not claim that exact request was marker-only.

## Risks / Trade-offs

Real opaque checkpoints still prevent foreign-provider replay. That is required
to avoid losing the whole compacted conversation. Unsupported marker extensions
need explicit qualification, not blanket deletion. Mock tests establish projection
and error contracts, not live OAuth eligibility.

## Migration Plan

No schema/configuration migration. Archive and release separately when authorized.
