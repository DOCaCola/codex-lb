# Surface Claude Progress Updates

## Why

Codex users steering a Claude turn often see no reply and conclude that the steer was ignored. The steer does reach
Claude: Codex appends it after the pending tool results, and codex-lb translates it into the user turn that carries
those results. Claude usually answers it in a progress update, the short note Opus 5.5, Sonnet 5.5 and Fable 5.1 write
before a tool call. Anthropic returns progress updates as signed `thinking` blocks, and with no `thinking.display`
these models default to `omitted`, which strips their text. codex-lb sends no display for Codex clients, so every
progress update reaches the client as an empty reasoning item.

Local evidence: four recent Opus 5.5 rollouts hold about 5,800 reasoning items, none with text. In 7 of 14 mid-turn
steers, no visible reply followed within six items; the usual sequence was `reasoning, reasoning, tool`, the shape
Anthropic documents for a reasoning block followed by a progress update and its tool call.

Third-party evidence: opencodex #7108 reports the same symptom for Opus 5.5 in the Codex App ("the agent looks like it
ignored them"); its PR #7143 requests `display: "updates"` and shows signed updates as visible commentary. CLIProxyAPI
measured Claude Code 2.1.280 sending `thinking.display: "updates"` with `thinking-display-updates-2026-08-18` for
Opus 5.5, Fable 5.1, Sonnet 5 and Sonnet 5.5 when the caller sets no display (`claudeModelUsesProgressDisplay`), so
the shape matches the client our OAuth profile follows.

## What Changes

- Translated Responses requests to a progress-update model with adaptive or budget thinking and no caller-chosen display
  send `thinking.display: "updates"` and negotiate `thinking-display-updates-2026-08-18`. An explicit `summarized`
  or `omitted` display is kept. Chat Completions already chooses `summarized` explicitly and is unaffected. Native
  Messages stays caller-owned; a native body that itself asks for `updates` gets the beta, like the binding beta.
- A completed signed `thinking` block with non-empty text under `updates` is delivered as a reasoning carrier with an
  empty summary, followed by its own done assistant message with phase `commentary` holding that text. The carrier's
  authenticated opaque state keeps the unchanged block and marks it as presented.
- Replay restores the signed block in place and drops the adjacent commentary copy whose text matches exactly. An
  edited or missing copy is replayed as the client sent it.
- Readable projections (compaction across accounts or models, OpenAI handoff) treat the commentary copy as the portable
  form of a presented update and do not convert the same text a second time.
- The translated stop diagnostic logs the number of progress updates delivered.

## Capabilities

### Modified Capabilities

- `claude-accounts`: translated Claude progress updates.

## Impact

- `app/modules/claude/capabilities.py`, `protocol.py`, `dispatch.py`, `inference.py`, `responses.py`, `opaque.py`,
  `replay.py`.
- Reasoning summaries stay empty on these models, as they already are under the `omitted` default.
- Older history without the presentation marker replays unchanged.
