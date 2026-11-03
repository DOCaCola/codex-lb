# Design

## Decisions

The reference lives with the cache-lineage state, which already tracks recent
Claude conversations. It is keyed by account and conversation, because message
IDs belong to one account. A request takes a ticket when it is prepared, carrying
the stored message ID or `null` and a send sequence. The projection's message ID
is recorded only after the stream stops with a stop reason. A ticket from an
earlier request never replaces a later reference. References expire after one
hour, the lifetime of the translated cache entries, and memory is bounded.

The `diagnostics` field changes every turn without affecting the prompt cache,
so the miss logger excludes it from parameter digests.

Anthropic's reason is logged as `claude_cache_diagnosis` with its type and missed
tokens, from `message_start`, `message_delta` or a non-streamed message.

## Alternatives

Injecting into native requests would override what Claude Code chose to send.
Persisting references would add a table for diagnostics only; after a restart
the first request per conversation simply sends `null`.

## Risks

The field and beta are part of Claude Code's own wire. A rejection would surface
as a 400 on translated requests; we only send IDs Anthropic issued to the same
account.
