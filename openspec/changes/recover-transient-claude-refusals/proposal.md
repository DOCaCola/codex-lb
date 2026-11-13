## Why

On 2026-11-13 between 10:22:04 and 10:22:22 UTC, seven Claude requests failed with `model_source_error` "Claude returned an error". Anthropic's edge had answered with a non-JSON 503 page. The gateway discarded that page, so clients and request logs lost the upstream reason. It also passed the refusal straight to Codex, because same-account recovery only accepted 529 or a 503 typed `overloaded_error`.

Codex treats the unknown code as a generic retryable error. It retries five times over about six seconds and then falls back from WebSocket to HTTP, so a short burst exhausts its budget. Claude Code itself retries 408, 409 and every status of 500 or above, unless Anthropic sends `x-should-retry: false`. CLIProxyAPI, opencodex, agent-lb and sub2api likewise treat upstream 5xx as retryable before any output has been streamed.

## What Changes

- Before any generation starts, Claude refusals with status 408, 409 or ≥ 500 are retried on the same account. Anthropic's `x-should-retry: false` is honoured. The shared four-send budget and ten-second recovery window are unchanged.
- Pre-dispatch connection retries and transient-refusal retries share one jittered, doubling wait sequence. Retry-After stays a minimum.
- Non-JSON error bodies from model sources keep their text. For HTML this is the page title; for other text it is a redacted, whitespace-collapsed excerpt of at most 1000 characters. Status and code are unchanged. Bodies are read with a bound and under the first-frame deadline.
- Native Claude Messages errors with non-JSON bodies keep their upstream status and text, where they previously became "Claude returned invalid JSON".

## Impact

- Specs: `claude-accounts`, `model-source-routing`, `openrouter-accounts`.
- Code: `app/modules/claude/overload.py`, `app/modules/claude/failover.py`, `app/modules/claude/transport.py`, `app/modules/model_sources/forwarding.py`, `app/modules/openrouter/errors.py`, `app/modules/openrouter/images.py`, `app/modules/proxy/api.py`.
- No settings, schema or client changes.
