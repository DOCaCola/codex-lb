# Show Claude reasoning summaries to Codex

## Why

Codex clients ask for reasoning summaries with `reasoning.summary` (`auto` by default, `concise` or
`detailed` when configured). Translated Claude Responses ignore that field: the thinking display is chosen
only from a non-standard `reasoning.display` field Codex never sends, and readable thinking reaches only Chat
Completions callers. Opus 5.5 therefore always runs with progress updates, Claude 4.7+/5.x adaptive models
return signature-only thinking, and a Codex user who configured detailed summaries sees no Claude reasoning.
A production investigation found 13 consecutive signature-only thinking blocks in one Opus 5.5 turn.

OpenCodex ef1ca714 (#7728) maps an explicit `concise`/`detailed` summary to `display: "summarized"` for
Opus 5.5 and keeps progress updates for `auto`, `none` or an omitted summary. Antigravity in this gateway
already shows thought summaries whenever a summary is requested.

## What Changes

- Derive the adaptive thinking display from `reasoning.summary` when the caller gives no explicit display:
  progress-update models use `summarized` for `concise`/`detailed` and `updates` otherwise; other adaptive
  models use `summarized` whenever a summary other than `none` is requested.
- Stream readable Claude thinking as a Responses reasoning summary (part added, text deltas, text done, part
  done) when a summary is requested and the display is not `updates`, matching Antigravity.
- Reject unknown `reasoning.summary` values.

## Impact

Translated Claude Responses only. Native Messages, Chat Completions reasoning and progress-update presentation
are unchanged. No schema, settings or catalog changes.
