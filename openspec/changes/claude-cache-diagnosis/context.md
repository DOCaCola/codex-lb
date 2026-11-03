# Evidence

Claude Code 2.1.317 (darwin-arm64 package, inspected 2026-11-03):

- Request: `diagnostics: {previous_message_id: <id> ?? null}` on agentic first-party requests with tools, with the `cache-diagnosis-2026-04-07` beta.
- Response: `message_start.message.diagnostics.cache_miss_reason`, overridden by `message_delta.delta.diagnostics.cache_miss_reason` (non-streamed: `message.diagnostics`).
- Reason types it recognises: `model_changed`, `system_changed`, `tools_changed`, `messages_changed`, `previous_message_not_found`, `unavailable`, with `cache_missed_input_tokens`.
- A 400 naming `diagnostics.previous_message_id` is only classified for telemetry (`previous_message_id_invalid`); it is a schema rejection of a malformed ID.

CLIProxyAPI at `6e6afab9` (2026-11-03), `internal/runtime/executor/claude_executor_diagnostics.go`
and `helps/claude_diagnostics.go`: injects the field into cloaked requests to
Anthropic (`inject-diagnostics`, default true) and adds the beta only when the
body carries it (`56e533fb` "pair diagnostics with cache beta"). The reference is
keyed by credential and session, kept for one hour, committed only after a
completed message, and ordered by request sequence so an older request cannot
overwrite a newer reference. No reference parses the response diagnosis.

OmniRoute (`open-sse/config/anthropicHeaders.ts`) includes the beta in its base set.
