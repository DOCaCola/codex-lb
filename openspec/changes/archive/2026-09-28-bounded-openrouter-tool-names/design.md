# Design

## Context
OpenRouter translates our Responses requests upstream. Long namespace flattening
can violate its selected endpoint's Chat tool-name constraint.

## Goals / Non-Goals
Preserve client identity through every tool-bearing request/response surface.
Do not rename native OpenAI or Claude traffic, rewrite arguments, or drop tools.

## Decisions
Use request-local typed identities and deterministic SHA-256 aliases in a reserved
ASCII namespace. Flatten Responses namespace declarations into independently named
tools before OpenRouter can create oversized names. Alias all namespaced tools;
alias oversized, invalid or reserved-prefix bare names too. Keep valid bare names.
Hash structured identities rather than flattened strings to avoid namespace
ambiguities. Fail explicitly on an actual alias collision.

Transform declarations, historical calls and explicit/allowed tool choices on a
copy. Restore Responses items and terminal output, Chat tool calls and stream
events. Reuse the existing SSE separator and byte limit; frame within the existing
transport iterator without spawned read tasks, preserving cleanup/deadlines.
Keep mapping per attempt, outside serialized payload and persisted history.

Reference inspection 2026-09-28: OpenCodex 3cc34e118192 (openai-chat/tool-name-registry.ts
and bounded-tool-names tests) covers the exact document tool identity, replay and
response restoration. Sub2API 9a62841fd124 uses hashed namespace flattening;
CLIProxyAPI acdace936fa7 uses truncation plus numeric disambiguation in its Codex
translator; OmniRoute a58000c7685f has hashed aliases enabled for NVIDIA only.
Adapt the design, not copied source. Unlike OpenCodex, include oversized bare names.

## Risks / Trade-offs
Alias leaks or missing replay mapping cause tool dispatch failure: exercise full
round trips, namespace collisions, stream chunking, historical-only identities.
Frame buffering: reuse the shared SSE byte limit and existing transport cleanup.
No live provider inference is required for local verification.
