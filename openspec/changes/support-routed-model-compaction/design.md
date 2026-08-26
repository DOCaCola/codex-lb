## Context

Codex remote compaction v2 is a normal Responses request ending in
`{"type":"compaction_trigger"}`. The client requires exactly one terminal
`compaction` output item whose `encrypted_content` it stores and replays.
OpenAI-compatible sources can summarize text but generally cannot interpret
the trigger or mint an OpenAI encrypted compaction blob.

## Goals / Non-Goals

**Goals:**

- Preserve native compaction for subscription-backed models.
- Let a source-owned model summarize its own history without client changes.
- Keep the compact response and replay contract valid for Codex.
- Prevent proxy-owned or native opaque blobs from reaching an incompatible
  destination.
- Reject incomplete or empty source summaries.

**Non-goals:**

- Teach external model sources the private OpenAI compaction protocol.
- Change Codex's provider-level compaction decision.
- Add a model-source capability setting.
- Change the standalone `/responses/compact` replacement-history contract in
  this change; the production failure uses remote compaction v2.

## Decisions

### Destination-aware compaction dispatch

Terminal compaction remains detected by the existing request-policy helper.
The HTTP route may select a Responses-capable model source for that request.
If no source is selected, the existing subscription compact service remains
unchanged.

### Synthetic source compaction

For a selected source, codex-lb removes the terminal trigger and upstream-only
controls, replaces images with an explicit omission marker, appends the Codex
handoff-summary prompt, and makes a non-streaming Responses request. Only text
from completed assistant message output is accepted.

The proxy returns the existing synthetic SSE compaction lifecycle with one
item. Its `encrypted_content` uses `clb1:` followed by base64-encoded UTF-8
summary text. The prefix is a serving-identity marker, not encryption.

### Replay lowering

Before any upstream egress, a valid `clb1:` item is replaced with a user
message containing the standard Codex summary prefix and decoded summary.
Malformed proxy-owned envelopes become an explicit unavailable-history note
rather than being forwarded as native encrypted state.

When the selected destination is a model source, remaining native opaque
compaction items also become the unavailable-history note. Subscription
destinations retain native opaque items unchanged.

### Native compact reasoning boundary

Immediately before a native compact request is sent, top-level reasoning items
have non-empty plaintext `content` replaced by an empty array and output-only
`status` removed. Ordinary model-source requests retain their provider-native
reasoning history.

## Failure Modes

- An upstream source error retains the existing model-source error envelope.
- An incomplete, malformed, or empty summary returns a 502 and does not install
  replacement history.
- A client disconnect follows the existing model-source settlement and cleanup
  path.
- Native opaque history switched to a source is represented explicitly rather
  than silently discarded.

## Example

```text
Codex compaction_trigger
  -> codex-lb selects LiteLLM source
  -> source receives ordinary summary request
  -> codex-lb returns compaction(clb1:<summary>)
  -> Codex replays item
  -> codex-lb lowers it to summary context before LiteLLM/OpenAI egress
```
