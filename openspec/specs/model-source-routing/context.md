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

Source summarization cannot itself resolve native continuation handles or decrypt native checkpoints. The fallback WebSocket replay store is not a general HTTP history materializer. Verified checkpoint provenance permits the on-demand native handoff described below; otherwise a request containing such state must supply complete materialized history or use the original native provider. Replacing it with a placeholder would falsely report successful compaction. Valid proxy-owned clb1 summaries remain portable. For example, a trigger-only request anchored to resp_old is rejected before provider dispatch instead of summarizing an empty conversation.

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
conversation. Without readable recovery or a verified native handoff it fails explicitly,
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

## On-demand native checkpoint handoff

Ordinary native compactions now capture only the original account/model and
native item metadata under a SHA-256 checkpoint digest, authenticated API key and
conversation/session. Neither the compact input, attachments nor ciphertext is
copied into this provenance record. Native wire output is unchanged and no summary
is requested. A successful compact over older opaque history can establish fresh
provenance because the native backend has processed it successfully.

Only a source switch that actually needs unreadable checkpoint context requests
a portable summary. Recovery order is an existing valid readable snapshot, a
valid cached handoff, then generation on the verified original native account and
model. Generation uses that exact checkpoint and a task-state handoff prompt,
without tools, truncation, destination continuation/affinity headers or unrelated
visible suffix. Current API-key model/account restrictions are rechecked even for
cache hits. Original account loss or native checkpoint rejection stops generation;
there is no cross-account failover, placeholder or shortened-history retry.

The native auxiliary request has its own handoff request ID, normal reservation,
admission, usage settlement and request log. It uses the existing tracked detached
persistence lifecycle; cancellation still owns reservation-release work. Only
complete, nonempty, nonrefused text becomes a portable summary. Surrounding visible
messages, tools and images stay ordered and unchanged. Summarization is lossy:
the prompt requests decisions, constraints, key evidence and unresolved work and
excludes obsolete plans and protocol chatter; it cannot promise every old fact.

Private integrity-checked stores retain provenance for 30 days (10,000 entries,
32 KiB per entry, 16 MiB total) and generated summaries for 30 days (1,000 entries,
512 KiB per entry, 64 MiB total). Reads do not extend expiry; oldest records can be
evicted earlier under those bounds. A valid summary can outlive its provenance
and does not need the old account to generate again. Cross-worker SQLite claims
prevent simultaneous duplicate generation. Generation has a 300-second budget;
claims expire after 330 seconds, and are released on success, error or cancellation.
A concurrent caller receives 503 compaction_handoff_in_progress with Retry-After2.
Storage coordination failures and unretained summaries fail explicitly.

The old checkpoint-history namespace remains readable for already-retained
complete snapshots until its existing one-hour expiry (1,000 entries, 256 MiB per
entry, 1 GiB total); normal native compactions no longer populate it. Its exact
recorded preserved-message prefix is deduplicated only directly before its
checkpoint, never by repeated user-text equality. All three namespaces are swept
by existing periodic replay maintenance.

For example, compact [user(task), tool-call, tool-result] natively: only provenance
is recorded. Later switch to Claude with [checkpoint, user(continue)]: the original
native account generates one metered handoff, and Claude receives that summary
plus user(continue). Repeated source turns reuse the summary; source continuation
retains the already-readable logical input. Remaining with native OpenAI never
generates a handoff. Unobserved legacy checkpoints without readable recovery or
verified origin still fail at the original input index. Destination capacity
refusals do not trigger automatic truncation or additional staged summarization.

References inspected on 2026-10-01: OpenCodex cae9b553e9b882dd13781a7f3ee6f68c0dcc8c4f
uses routed ocx1 summaries but native-blob placeholders; Sub2API
42bc7f6cffe24bcb471608e48e66b4a0afa1f882 omits unknown checkpoints; CLIProxyAPI
97f244b8ddb9cbf564b6e6faab0159102cca8617 warns/omits unmapped items; OmniRoute
fc5e2bccd4f70fecf5aab94dfb8136c74ab5a21b rejects them on its normal translator.
None implements this verified native-to-source on-demand handoff. Tests qualify
local HTTP/WS routing, caching, ownership, cancellation and accounting against
mock upstreams; real native checkpoint acceptance and summary quality still need
live qualification. No client changes are required.

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

Claude signed blocks are authenticated before routing. Completed thinking prefers
its original account and model, where it is replayed verbatim. On another route,
or after the upstream rejects a historical signature, the summarizer receives
completed thinking as readable assistant text; redacted thinking has no readable
content and is omitted. Active-turn signed state and hosted search remain hard
account/model owners and fail explicitly when unavailable. Pending tool calls also
fail unless their real outputs are supplied; no tool output or signature is
invented. Native Messages and ordinary Responses recovery retain their existing
omission policy. See `../claude-accounts/context.md` (portable signed history,
2026-10-01) for why the earlier hard-owner rule was replaced.

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

## Post-start Responses forwarding failures

Responses streams use an outer protocol-only error serializer around the shared
settlement owner. A forwarding failure first closes the attempt, releases its
reservation/admission and logs its original cause, then emits one `error` event.
For example, a Claude projection error after assistant text becomes
`{"type":"error","status":502,"error":{"code":"invalid_upstream_response",...}}`
over both HTTP SSE and the in-process WebSocket bridge. Only validated
Retry-After metadata may appear alongside it; arbitrary upstream headers do not.

The error is not a successful completion, does not seed successful replay state,
and does not initiate another generation. A later valid turn can use the same
socket. Native Messages and Chat keep their existing protocol serializers.
Cancellation and programming exceptions are not converted into protocol errors.
If cancellation arrives during settlement, cleanup and the original failure log
finish before cancellation propagates; no synthetic error goes to the departed
client. An already delivered terminal is never followed by a second terminal.
