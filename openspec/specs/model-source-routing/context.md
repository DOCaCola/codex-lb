# Model Source Routing — Context

## Purpose

Capability-based routing and accounting for OpenAI-compatible model sources,
including field-preserving embeddings forwarding.

This capability keeps source selection separate from subscription-account
routing: embeddings traffic is served only by sources that declare the
embeddings capability, while Responses/chat/audio continue to use their own
capability gates. Field presence (including explicit nulls) is preserved on
embeddings forwards so compatible sources see the same payload shape the
client sent.

## Fork compaction history safety

Source summarization cannot resolve native continuation handles or decrypt native checkpoints. The fallback WebSocket replay store is not a general HTTP history materializer. A request containing such state must supply complete materialized history or use the original native provider; replacing it with a placeholder would falsely report successful compaction. Valid proxy-owned clb1 summaries remain portable. For example, a trigger-only request anchored to resp_old is rejected before provider dispatch instead of summarizing an empty conversation.

Subscription overflow uses the same source summarization protocol while retaining its original admission claims, dispatch attribution and settlement owner. Rejection before ownership transfer releases the overflow claim without a source call or reservation.
