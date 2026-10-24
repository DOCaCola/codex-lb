# Tasks

## 1. Routing and dispatch

- [x] 1.1 Extract the post-parse `v1_responses` dispatch into a function shared with the Messages ingress, with an
  output projection parameter.
- [x] 1.2 Route `claude_messages` by model after API-key enforcement: `anthropic/` and `claude-` to the native
  path; authorized Responses models to translation; otherwise an Anthropic error before dispatch.
- [x] 1.3 Identify the Messages ingress in request logs.

## 2. Request translation (`app/core/messages/`)

- [x] 2.1 System, developer, text, image, PDF, tool_use and tool_result mapping; billing attribution removal.
- [x] 2.2 Tool conversion: schema cleanup, non-strict, deterministic 64-character aliases for names and call IDs,
  tool_choice and parallel control, web search mapping, rejection of other server tools.
- [x] 2.3 Sampling, limits, output format and fast-mode mapping; rejection of fields Responses cannot honor.
- [x] 2.4 Effort and summary mapping.
- [x] 2.5 Session and agent identity, prompt-cache key and cohort fallback.

## 3. Reasoning envelope

- [x] 3.1 `clb1:` encode and verify with the installation key; replay to the same model only; omit other cases;
  reject forged envelopes.
- [x] 3.2 Native Claude path: remove envelope thinking blocks and assistant messages left empty.

## 4. Response and error projection

- [x] 4.1 Streaming projection: held `message_start`, thinking with signatures, commentary as unsigned thinking,
  text, deferred `tool_use`, web search blocks, alias restoration, stop reasons and usage.
- [x] 4.2 Non-streaming aggregation.
- [x] 4.3 Pre-output HTTP errors (including the "prompt is too long" overflow) and post-output in-band errors.
- [x] 4.4 Local `count_tokens` estimate for translated models.

## 5. Verification

- [x] 5.1 Unit tests for every mapping, the envelope, identity, error and usage rules, including reference
  regressions (long names, PDF, commentary, deferred tool start, cache deduction).
- [x] 5.2 Integration tests through the shared dispatch for a native account and an OpenRouter source.
- [x] 5.3 OrbStack mock qualification: Claude Code → codex-lb → mock Responses upstream, covering tool turns,
  reasoning replay, subagents, web search, overflow-driven compaction, and a GPT→Claude switch against the mock
  Anthropic upstream.
  Qualified with Claude Code 2.1.283: text, tool turn, reasoning replay, overflow-driven compaction and the GPT→Claude
  switch. Subagents and web search are covered by unit tests; Claude Code itself drops foreign thinking blocks on the
  switch, so envelope stripping is covered by unit tests.
- [x] 5.4 Full test suite, ruff, ty and `openspec validate --strict`.

## 6. Documentation

- [x] 6.1 `messages-api-compat` context and user docs: Claude Code configuration with per-family model settings.
