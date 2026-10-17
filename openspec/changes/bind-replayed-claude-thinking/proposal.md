# Bind Replayed Claude Thinking

## Why

Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 bind each signed thinking block to the system prompt, tool list and
earlier messages it was created under. A replay under a different prefix fails with HTTP 400 "Invalid `signature` in
`thinking` block. The block is bound to a different conversation". Codex translation, reconnects, model switches and
tool-list changes all reshape that prefix. Our one-shot signature recovery repairs this only by removing every
historical thinking block, skips requests carrying server-tool history, and repeats the failed send on every turn.

CLIProxyAPI 911f49c (issue #6692) opts such requests into Anthropic's `thinking.block_binding` control with
`prefix_mismatch_behavior: "drop_block"` plus the `thinking-binding-controls-2026-08-01` beta. The reporter verified
the same stale block live: HTTP 400 without the control, HTTP 200 with it. opencodex, sub2api and OmniRoute pair the
same beta with a caller-supplied binding.

## What Changes

- Requests to a preserved-thinking model that replay a signed `thinking` or `redacted_thinking` block default
  `thinking.block_binding.prefix_mismatch_behavior` to `drop_block`, for translated and native requests and token
  counting. Haiku and Sonnet 5.5 qualify only with adaptive thinking; Opus 5.5 and Fable 5.1 also with manual budgets.
  A caller-chosen behavior is kept.
- Any request whose body carries `thinking.block_binding` sends the binding-controls beta.
- Historical signature recovery is unchanged and remains the path for other models.

## Capabilities

### Modified Capabilities

- `claude-accounts`: preserved-thinking prefix binding.
