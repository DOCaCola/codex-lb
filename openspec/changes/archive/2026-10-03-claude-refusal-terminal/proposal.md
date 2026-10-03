# Report Claude refusals as content filtering and log Claude stop reasons

## Why

Translated Claude Responses map `stop_reason: "refusal"` to `response.incomplete` with `content_filter` only for Chat projections with visible reasoning. Every other Responses client, including Codex, receives a refusal as `response.completed`. Codex has dedicated recovery for `content_filter` (it records content-filter guidance and retries the sampling request), and that recovery never runs because the turn looks successful. The client instead ends the task silently.

On 2026-10-03 between 00:45 and 01:09 UTC, ten of 181 retained Opus 5.5 responses in threads `01a0f38a` and `01a0fd60` ended with only reasoning or no output, and Codex recorded each as a completed task with no message. codex-lb does not record Claude's stop reason anywhere, so these incidents cannot be classified as refusal, empty `end_turn` or another cause.

References (inspected 2026-10-03):

- OpenCodex `249462bf5` maps `refusal` and `content_filter` to an incomplete `content_filter` result and keeps usage (its #4312).
- CLIProxyAPI `2044a01f4` maps `refusal` to `content_filter` on its Chat projection; its Responses projection still reports completed.
- Codex `codex-api` maps `response.incomplete` with `content_filter` to `ApiError::ContentFilter`; `core` adds `ContentFilterGuidance` before retrying.

## What Changes

- A Claude `refusal` stop reason becomes `response.incomplete` with `incomplete_details.reason = "content_filter"` for every translated Responses and Chat projection, independent of reasoning display. Output and usage are preserved.
- Each translated Claude message stop logs one count-only line: response ID, model, stop reason, resulting status, upstream content block type counts and output tokens. No text, reasoning, tool input or signatures.
- Unchanged: native Anthropic Messages passthrough (the client receives the raw stop reason), `max_tokens` and `pause_turn` handling, and successful `end_turn` / `tool_use` turns.

## Capabilities

### Modified Capabilities

- `claude-accounts`: refusal terminal semantics and stop-reason diagnostics for translated Claude responses.

## Impact

- Codex clients see a content-filter error and apply their own guidance-and-retry recovery instead of a silent stop.
- Future empty or reasoning-only Claude turns can be classified from logs.
- `app/modules/claude/responses.py`, `tests/unit/test_claude_protocol.py`, claude-accounts context notes.
