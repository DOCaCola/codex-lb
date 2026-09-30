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

## Complete source compaction input

Native compact serialization retains its upstream-specific 100k estimated-token
wire reduction. Source summarization does not use that serializer: continuation
is materialized from the validated complete request first, and a stateless,
tool-free summarization request preserves readable text/tool/image history.
Control-only trigger and additional-tools declarations are removed, not history.
Automatic input truncation is disabled and source model overrides cannot replace
history/instructions, enable tools/structured output or restore continuation
handles. Compatible generation controls such as reasoning still apply.

Provider capacity, not the conservative client default, determines whether the
complete request fits. No JSON-character admission guess or shortened-history
retry is added; inline image bytes are not text tokens. A real capacity/size
refusal or incomplete output returns an error and leaves the original retained
anchor available. For example, a 150k-token-equivalent tool transcript on a
1M-capacity Opus is not trimmed to the native compact budget. A request that
really exceeds Opus capacity is rejected instead of falsely reporting successful
compaction after discarding items. Existing native compact behavior is unchanged.

Claude signed blocks are authenticated and treated as hard account/model owners
for compaction, including completed thinking. Mixed signed owners, model changes,
unavailable owners and invalid signatures fail explicitly rather than invoking
ordinary conversation recovery that omits thinking. Pending tool calls also fail
unless their real outputs are supplied; no tool output or signature is invented.
Native Messages and ordinary Responses recovery retain their existing policy.

OpenCodex at 5ab6d52b2a4da722d398e4ab50a6c621ac3ce087 informs the history-first
approach. Its merged #6175 older-image omission is heuristic; this source path
preserves images instead. No staged multi-call summarization is implemented:
references did not establish a proven complete staged Claude recipe. Complete
input coverage does not guarantee every fact survives an LLM summary, and already
omitted facts cannot be recovered from old checkpoints alone.

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

## Source WebSocket error metadata

The bridge forwards only a validated Retry-After header in error event headers,
using the existing bounded delta-seconds/HTTP-date parser. It does not forward
cookies or credentials. For example, source429 plus Retry-After12 remains429
with headers={"retry-after":"12"} over WS. No successful completion is synthesized.
OpenCodex's safe error-envelope forwarding is the reference; client retry policy
is separate from the gateway's obligation to preserve the signal.
