## Context
Codex's incremental WebSocket protocol assumes the preceding response is recoverable. Our per-turn HTTP fallback does not provide upstream storage. See context.md for the OpenCodex reference and concrete failure sequence.

## Goals / Non-Goals
- Restore incremental HTTP-fallback conversations without repeated upstream misses.
- Preserve native WebSocket behavior, routing policy, settlement, and client recovery.
- Do not enable upstream store=true or expose a conversation archive API.

## Decisions
- Retain original full input plus completed output, keyed by API key, conversation, and response id.
- Expand before normalization and policy evaluation. Deduplicate only a complete prefix containing provider output identity.
- Keep a 64 MiB resident serialized cache and bounded atomic disk files, with one-hour expiry and periodic cleanup.
- Use transport evidence from request logs to reject known HTTP cache misses before dispatch.
- Preserve completion settlement on cache failure; permit the client's existing full-history recovery.

## Risks / Trade-offs
- Conversation plaintext is retained temporarily on the proxy filesystem with private permissions.
- Full histories duplicate content across responses; byte and entry budgets bound retention.
- Cache loss or replica-local misses still require a client retry. No silent context truncation is permitted.

## Migration Plan
No application database migration is required. Existing request-log transport metadata identifies ephemeral owners. Previously mislabeled legacy entries retain existing recovery behavior until replaced by newly completed cached turns.
