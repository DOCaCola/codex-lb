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

## Local compaction markers versus opaque checkpoints

A local `context_compaction` marker can contain only its type, optional ID and
internal message metadata, with missing/null `encrypted_content`. Its summary is
an independent ordinary message. Source projection removes this control marker
only from wire input: the summary, tools, images and retained logical history
remain intact. For example, switching to Claude with `[context_compaction,
user("Readable summary"), user("Continue")]` sends the two readable messages.
Native OpenAI requests keep the original marker.

An encrypted native checkpoint is different: it may contain the entire compacted
conversation. Without a verified readable recovery record it fails explicitly,
as do empty/wrong-typed ciphertext,
unknown marker payload fields and corrupt `clb1:` summaries. There is no attempt
to decrypt it, invent a summary, silently discard history or modify client files.
Projection validates the whole input before replacing it; rejection identifies
the original `input[N]`. Logs expose only request ID, index, known subtype,
ciphertext presence and classification reason, or an aggregate skipped count.

Reference inspection on 2026-09-30: OpenAI Codex
`ed0cc1a4ab30e1e83f1214e7a368c55b83fd089d`, `protocol/src/models.rs`, declares
optional ciphertext on ContextCompaction. OpenCodex
`569e3e7dae48bafc54b8a1a7e3a85129befe2d98`, `src/responses/parser.ts`, omits
local markers because their summary follows as an ordinary message. Its fallback
note for unreadable native checkpoints is not adopted. The production rejection
at 2026-09-30T16:53:37Z lacked subtype/body diagnostics; it does not prove that
particular request was marker-only.

## Verified readable checkpoint recovery

Successful native compact-service calls and full-input native WebSocket compaction
completions bind the checkpoint's SHA-256 digest to the readable logical input.
Publication follows usage settlement and precedes returning the compact result.
This is recovery of visible input, not decryption of native private state.
An authenticated API key and a real conversation/session identity are required;
anonymous requests and generic source fallback scopes do not seed shared records.

Messages, original instructions, readable reasoning, direct tool call/result pairs
and attachments remain intact. Transport IDs/status/telemetry, tool advertisements,
payload-free local markers and reasoning ciphertext are not retained. Mirrored
reasoning summary/content is kept once. No old task messages or tool evidence are
discarded on a guess that they are unimportant. Unknown semantic state, hosted
resources, unresolved native handles, unpaired outputs and empty readable input
make the checkpoint ineligible rather than publishing partial recovery.

Records live in the private checkpoint-history namespace and reuse atomic,
integrity-checked replay storage: one-hour TTL, up to 1000 entries, 256 MiB per
entry and 1 GiB total, with bounded memory and periodic cleanup. Reads do not
extend expiry. Native encrypted checkpoints are never stored in the record body;
the key is a digest, scoped by API key and conversation. A chained compact stores
its complete materialized readable input, so expiration of its predecessor does
not invalidate the new record.

For example, compacting [user(task), tool-call, tool-result] through the native
compact endpoint returns the unchanged OpenAI checkpoint. Switching to Claude
with [checkpoint, user(continue)] in the same scope restores the retained visible
context before policy checks. A v1 preserved-message prefix is replaced only if
it exactly matches the recorded compact result, preventing duplication without
heuristic text deduplication. Source continuation then retains the materialized
input, so later expiry of the native record does not erase that successful switch.

This does not recover unobserved legacy checkpoints, native handle-only history,
or provider-private resources. Generic native V1 generation streams remain
unchanged; their compact endpoint is the capture surface. If recovered history
exceeds the destination's capacity, its refusal is returned without truncation or
a silently billed extra summarization call. Logs contain counts and bounded
reasons, never messages, identifiers or ciphertext.

Source inspection on 2026-09-30 found omission rather than readable recovery in
Sub2API 42bc7f6c (#5084 merged July 31; #6397 merged September 5), and warnings plus
omission in CLIProxyAPI 97f244b8 (#5516 closed without merging). OmniRoute dbe703a0
rejects unsupported types on the normal translation path and uses a placeholder
in its ChatGPT-web bridge. None establishes native checkpoint decoding; their
gateway-owned portable envelopes remain distinct from this retained-input mapping.

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
