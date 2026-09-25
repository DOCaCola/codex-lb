# Claude accounts

Specification: [Claude accounts](../openspec/specs/claude-accounts/spec.md).
Operational details: [implementation context](../openspec/specs/claude-accounts/context.md).

## Set up

1. Open **Accounts → Add account → Claude**.
2. Acknowledge that this gateway will be the sole refresh consumer for the grant.
3. Complete OAuth sign-in, or explicitly upload your Claude Code credential JSON.
4. Refresh the account, select models, and save context/output limits. New models
   stay disabled until selected. The default context cap is 200,000 tokens.
5. Grant source-restricted client API keys access to the Claude account source.

Codex clients use `anthropic/<model-id>` over Responses HTTP or WebSocket. Native
Messages clients can use the upstream model ID or its `anthropic/` prefix on
`/v1/messages`; token counting is at `/v1/messages/count_tokens`. No LiteLLM hop
is required. OpenAI models remain first in the Codex list, then native Anthropic,
then other provider sources.

## Operate and recover

Pause/resume, quota monitoring, model selection and reconnect are in the shared
account detail. Unknown quota is not zero usage. Model-specific exhaustion only
blocks applicable models. API-equivalent costs are not subscription charges.

An uncertain rotating refresh requires reconnect with a fresh grant. Reconnect
must authenticate the same account and organization. A different account should
be added separately. Importing an expired file defers identity verification until
refresh succeeds; an unverified account which cannot refresh must be re-enrolled.

The global version control follows stable Claude Code releases daily, or can pin
an exact version for rollback. It changes the advertised CLI version, not the
installed software or the compatibility policy.

Native signed history retains account ownership for one hour after its last
claim. Responses replay has one-hour retention as well. After retention expires,
resend portable context. Do not move signed thinking across accounts or models.

## Supported boundaries

Responses supports text, HTTPS/base64 images, function tools, unconstrained custom
tools, namespaces, adaptive reasoning on explicitly supported models and JSON-schema
output. Unsupported grammar-constrained decoding, uploaded files, Responses built-in
server tools, verbosity, automatic truncation and paid service-tier semantics fail
explicitly. A client that requests these must remove or adapt those controls.

Tests cover local mock and loopback paths, not live OAuth eligibility or included
subscription usage. Qualify both before production use. Upstream eligibility errors
are returned without hidden paid fallback or repeated account hopping.
