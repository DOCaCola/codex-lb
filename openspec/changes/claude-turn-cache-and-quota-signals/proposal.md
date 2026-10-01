## Why
Three Claude gaps surfaced while tracing a 429 and fast five-hour usage on
2026-10-01:

- **Turn-start cache rewrites.** By default Anthropic strips thinking from
  earlier assistant turns. Translated history carries signed thinking, so the
  prefix changes whenever a new user turn starts, and only the tools prefix is
  served from cache. Two production requests 6 s apart (17:23:48Z/17:23:54Z)
  projected to identical system, tools, breakpoints and first 858 blocks, yet
  the second rewrote everything after the 53K-token tools prefix. Such rewrites
  cost about $22 of $162 between 12:20Z and 17:30Z. Claude Code 2.1.220 sends
  `context_management: {"edits":[{"type":"clear_thinking_20251015","keep":"all"}]}`
  with `context-management-2025-06-27` on every Messages request when thinking
  is enabled or adaptive (CLIProxyAPI d33f63f8, 2026-09-29,
  `claude_executor_cloaking.go`); Anthropic rejects the edit otherwise.
  opencodex and OmniRoute also negotiate the beta.
- **Lost quota readings.** History sampling skips a sample less than 60 s
  after the previous one when the reset deadline is unchanged, even when
  utilization changed. A 100% five-hour reading 27 s after 99% was never
  stored, so the trend never showed the exhaustion that blocked the owner.
- **Misleading client error.** A quota-only Claude refusal reaches Responses
  clients as `rate_limit_error`. Codex (openai/codex d6c3b44,
  `codex-api/src/api_bridge.rs`) treats only `type: usage_limit_reached` as a
  usage limit with a reset time, and parses `resets_at` as integer seconds; any
  other 429 is retried and shown as "exceeded retry limit". The detail also
  carries a fractional `resets_at`.

## What Changes
- Translated requests with thinking `enabled` or `adaptive` send
  `clear_thinking_20251015` with `keep: "all"` and negotiate
  `context-management-2025-06-27`. Native requests are unchanged.
- Quota history stores every changed utilization or reset deadline;
  only unchanged repeats are bounded to one per account/window/minute.
- Quota-only Claude pool refusals use `type: usage_limit_reached` on OpenAI
  envelope surfaces (Responses HTTP/WebSocket); native Messages keeps
  Anthropic's `rate_limit_error`. `resets_at` is integer Unix seconds,
  rounded up like Retry-After. Codes and statuses are unchanged; no
  `plan_type` is sent, because it names ChatGPT plans.

## Capabilities
### Modified Capabilities
- `claude-accounts`: thinking retention on translated requests, quota history
  sampling and Responses quota error shape.

## Impact
Retained thinking counts as input context, as for Claude Code. No migration.
Upstream Anthropic 429 passthrough is unchanged; the refusal is recorded as
quota evidence, so a client retry receives the usage-limit error.
