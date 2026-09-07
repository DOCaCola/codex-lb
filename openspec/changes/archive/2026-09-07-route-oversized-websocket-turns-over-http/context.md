# Context

The observed request was 20,860,306 bytes, above the configured 15 MiB upstream WebSocket budget. Inline images after the most recent user turn could not be slimmed. The previous client-facing 413 recovery consumed Codex retries and disabled WebSocket across its session.

OpenCodex #2473 demonstrates pre-send per-turn HTTP selection. This implementation keeps the existing 128 MiB client ingress limit, reuses account-bound upstream routing and the service's event association/settlement, and bounds event buffering to one event per connection. Closing the connection cancels and joins producers. The adapter never retries sent turns. Upstream HTTP errors still go through existing Responses event handling; only HTTP 413 is mapped to context_length_exceeded.

Continuation IDs remain upstream-owned. Transport selection forwards previous_response_id unchanged; it does not invent storage, discard an anchor, or silently reconstruct unknown context. Existing service recovery remains responsible for a provider rejecting an anchor.

Compaction remains a separate context operation. Transport size alone does not authorize deleting images or tool results, and this change does not alter compaction summaries.
