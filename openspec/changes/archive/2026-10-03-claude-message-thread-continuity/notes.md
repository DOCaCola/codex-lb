## Reference evidence

Inspected CLIProxyAPI revision `d7914afdedca7af95ee974a42453dc49fc1388ce`
and its reports on 2026-10-03:

- [Issue 6346](https://github.com/router-for-me/CLIProxyAPI/issues/6346):
  thread continuations can omit earlier history and inherited tools. Our native
  forwarding does not rename tool names, so an alias cache is not required.
- [PR 6345](https://github.com/router-for-me/CLIProxyAPI/pull/6345):
  proposed missing-thread 404 normalization to trigger Claude Code's own replay.
  This was an open proposal, not evidence of a released fix.

Ownership reuses the existing account-provenance store with a separate
`message_thread` hash namespace. Retention is the existing sliding 30-day TTL.
Neither message identifiers nor conversation contents are retained.

## Independently verified client recovery

Claude Code 2.1.283 ran against codex-lb and a synthetic Anthropic server on
an internal OrbStack Docker network, using synthetic credentials only.
`CLAUDE_CODE_TETHER_LIVE=true` enabled the client's Message Threads path for
qualification; this does not establish its default rollout or real OAuth
entitlement. The mock explicitly rejected the first continuation with a 404.

Observed wire sequence:

1. Thread create: two Messages entries and 25 tool definitions; mock returned
   a Bash tool call and `msg_lab_1`.
2. Thread continue: `previous_message_id=msg_lab_1`, tool result, truncated
   history; codex-lb returned normalized HTTP 404.
3. Automatic thread create: four Messages entries, including the original
   history, assistant tool call and user tool result. All 25 tool definitions
   exactly matched the first request. Client finished with `LAB_TOOL_COMPLETE`.

No gateway-side generation retry or account cooldown was used. Route tests
separately establish exact-account ownership after soft-affinity expiry,
API-key/model isolation, paused-owner refusal, expired-state replay errors,
unrelated 404 preservation and publication suppression on persistence failure.

The relevant integration/resource suites pass: 163 tests. Strict change
validation and changed-file lint/format checks pass. Type checking
remains at the pre-existing 598 diagnostics, with no new diagnostics.
