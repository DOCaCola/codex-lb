# Claude accounts

Specification: [Claude accounts](../openspec/specs/claude-accounts/spec.md).
Operational details: [implementation context](../openspec/specs/claude-accounts/context.md).

## Set up

1. Open **Accounts → Add account → Claude**.
2. Acknowledge that this gateway will be the sole refresh consumer for the grant.
3. Complete OAuth sign-in, or explicitly upload your Claude Code credential JSON.
4. Refresh the account, select models, and save. Context and output capabilities
   are discovered automatically; there are no manual token-limit editors.
   New models stay disabled until selected. Models with unresolved limits cannot
   be enabled until discovery or maintained metadata supplies both limits.
5. Grant source-restricted client API keys access to the Claude account source.

Codex clients use `anthropic/<model-id>` over Responses HTTP or WebSocket. Native
Messages clients can use the upstream model ID or its `anthropic/` prefix on
`/v1/messages`; token counting is at `/v1/messages/count_tokens`. No LiteLLM hop
is required. OpenAI models remain first in the Codex list, then native Anthropic,
then other provider sources.

## Model budgets

Codex receives the full discovered context capacity, a 95% effective-context
percentage and a separate auto-compaction threshold at 90% of capacity. These are
client hints, not a guarantee about quality at maximum context. For example,
a 1,000,000-token context advertises a 900,000-token compaction threshold.

Translated requests without an output budget use the smaller of 64,000 tokens and
the model's maximum output. Explicit native or translated budgets remain accepted
up to that maximum. A 128,000-token output capability therefore does not force every
request to reserve 128,000 tokens.

Upgrading preserves selected model IDs and removes former manual budgets.
Existing projections stay disabled until a successful catalog refresh resolves
their limits. Discovery errors remain visible; no guessed generic limits are used.

## Operate and recover

Pause/resume, quota monitoring, model selection and reconnect are in the shared
account detail. Routing policy offers Normal, Burn first and Preserve within the
Claude pool, using the same strategy-specific semantics as Codex. Hard owners and
eligible conversation affinity still take precedence. Unknown quota is not zero usage. Model-specific exhaustion only
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

Native Claude feature negotiation and reviewed SDK/helper/agent headers are
preserved. Session headers and structured JSON `metadata.user_id` session fields
are projected together into the selected account/client scope; logical history
is unchanged. Conflicting session identifiers, malformed metadata and opaque or
legacy concatenated user IDs fail explicitly. Omit optional user metadata or
use the current structured Claude Code format. Do not forward your upstream
credentials as client metadata; codex-lb selects stored credentials separately.

Native request IDs remain available for correlation. Token-counting and supported
Haiku probe/title helpers have separate compatibility handling. These policies
are specified in [Claude accounts](../openspec/specs/claude-accounts/spec.md).

Responses supports text, HTTPS/base64 images, function tools, unconstrained custom
tools, namespaces, adaptive reasoning on explicitly supported models and JSON-schema
output. Unsupported grammar-constrained decoding, uploaded files, Responses built-in
server tools, verbosity, automatic truncation and paid service-tier semantics fail
explicitly. A client that requests these must remove or adapt those controls.

Tests cover local mock and loopback paths, not live OAuth eligibility or included
subscription usage. Qualify both before production use. Upstream eligibility errors
are returned without hidden paid fallback or repeated account hopping.

## Metadata refresh and rate limits

Usage is polled every three minutes and the model catalog every six hours.
Refresh can update successful cached readings sooner, but cannot bypass a running
refresh or an upstream-error cooldown. Concurrent refreshes share stored results.

A metadata 429 does not mean inference is unavailable. The account detail identifies
the failing endpoint, HTTP status and retry deadline. The gateway honors
`Retry-After`, or waits three minutes when no valid hint is present, across workers
and restarts. Last good readings retain their original timestamps and show as stale;
fresh inference headers can still update their own quota windows. Catalog and usage
cooldowns are independent. No account pause or reactive token refresh is triggered.
