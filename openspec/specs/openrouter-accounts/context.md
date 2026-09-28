# Implementation context

OpenRouter accounts reuse model-source scoping, encrypted inference credentials and accounting rather than masquerading as subscription accounts. An extension table stores the synchronized provider snapshot, operator selections and optional management credential. Optimistic version checks prevent a slow refresh from overwriting an operator's concurrent selection edit.

The client WebSocket bridge follows OpenCodex's separation of downstream transport from provider transport: it calls the existing Responses route in-process, streams SSE events as WebSocket frames, and closes owned work on disconnect. It does not imitate OmniRoute's proprietary `/v1/ws` protocol or require OpenRouter to accept upstream WebSockets.

OpenRouter's Responses API rejects stored continuation. Existing private replay storage materializes complete history, using client-key and conversation identity. Unknown handles produce an explicit full-resend request. No account substitution occurs after response delivery begins. Provider 403 responses are not retried across credentials; the gateway does not attempt to bypass access or moderation restrictions.

For example, selecting `z-ai/glm-5.3-flash` publishes `openrouter/z-ai/glm-5.3-flash` with a default 262144-token cap. The upstream receives `z-ai/glm-5.3-flash`, price-first provider selection and `store:false` over HTTPS while Codex receives events on its existing WebSocket.

Operator setup and monitoring details: [native OpenRouter accounts](../../../docs/openrouter-accounts.md).

## Provider error diagnostics

OpenRouter 403 does not establish invalid credentials: key spending restrictions,
funding or provider policy can also deny a request. Responses forwarding preserves
that status and a sanitized reason. Upstream 401 remains a generic proxy-credential
502 without reading its body; this prevents downstream clients from mistaking the
gateway's rejected provider key for their own authentication failure. Unknown
OpenAI-compatible sources retain their existing 401/403 credential protections.

For example, a 400 with `message: "Provider returned error"` and structured
`metadata.raw.error.message` now includes the nested reason and provider name in
the main error message. Existing request logs therefore retain the explanation
without requiring whole-conversation archiving. Only message/code/type/param and
the formatted provider diagnostic are exposed, never arbitrary raw metadata.
Malformed, non-JSON or oversized bodies retain a generic status-bearing error.
Unstructured raw strings are not echoed. Error reads are bounded at 64 KiB and
messages at 2048 characters, with secret redaction before truncation.

Reference inspection on 2026-09-28: OpenCodex `3cc34e118192` uses bounded/redacted
provider error text; OmniRoute `a58000c7685f` exposes sanitized upstream details
and distinguishes several non-auth 403 causes; CLIProxyAPI `acdace936fa7` retains
raw status/body (not adopted for our credential-bearing gateway); Sub2API
`9a62841fd124` extracts and sanitizes upstream messages. These are source findings,
not live qualification or proof of specialized OpenRouter raw-metadata handling.
Exact paths and revisions are recorded in the `openrouter-error-diagnostics`
change design. No implementation was copied.

This improves future evidence only: discarded historical 403 bodies and provider
details missing from historical 400 records cannot be recovered by this change.

## Unified account presentation

The dashboard uses one card/list collection for native and OpenRouter accounts; Accounts uses one search/filter list and a shared detail column. The add-account chooser includes OpenRouter. Provider-specific controls stay in the selected account's details, not a separate top-level provider section.

For example, select **Add account → OpenRouter**, save an inference key, and choose **Models** in the resulting detail view. Dashboard **Details** links retain the source ID in the selected query parameter. Dollar balances never contribute to Codex quota aggregates. Name sorting includes both providers, while native-only quota/reset sorts place OpenRouter accounts last.
