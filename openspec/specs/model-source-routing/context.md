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

## Dashboard model editor

In Settings → Advanced settings → Model sources, create or edit a source to
manage its models individually. URL, credential and supported endpoint protocols
remain source-level settings. Select a model to edit its ID, friendly name,
enabled state, limits, capabilities, reasoning settings and rates.

The existing models API persists these fields; no migration or pricing engine
change is needed. For example, setting model A's output price to 2.25 leaves
model B's 1.50 rate and provider-specific request overrides untouched. Blank
rates are sent as null, while an explicit zero is retained as a free rate.
The source summary shows each model's rates instead of presenting the first
model's prices as source-wide prices.

Rows use stable UI keys independent of editable model IDs. Duplicate/empty IDs,
invalid prices and nonintegral token limits prevent submission. Unchanged raw
metadata is preserved verbatim, and reasoning edits merge only the existing
reasoning keys. Cancelled drafts are discarded on reopening the dialog.
