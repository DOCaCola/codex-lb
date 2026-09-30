# Claude accounts

Specification: [Claude accounts](../openspec/specs/claude-accounts/spec.md).
Operational details: [implementation context](../openspec/specs/claude-accounts/context.md).

## Set up

1. Open **Accounts → Add account → Claude**.
2. Acknowledge that this gateway will be the sole refresh consumer for the grant.
3. Complete OAuth sign-in, or explicitly upload your Claude Code credential JSON.
4. Refresh the account, select models, and save. Context and output capabilities
   are discovered automatically; there are no manual token-limit editors.
   By default, new models stay disabled until selected. The **All models** toggle
   opts into automatic availability of eligible discovered models while retaining
   saved selections. Models with unresolved limits cannot
   be enabled until discovery or maintained metadata supplies both limits.
5. Grant source-restricted client API keys access to the Claude account source.

Codex clients use `anthropic/<model-id>` over Responses HTTP or WebSocket. Native
Messages clients can use the upstream model ID or its `anthropic/` prefix on
`/v1/messages`; token counting is at `/v1/messages/count_tokens`. No LiteLLM hop
is required. OpenAI models remain first in the Codex list, then native Anthropic,
then other provider sources.

OpenAI Chat clients can use an enabled `anthropic/<model-id>` on
`/v1/chat/completions` with either JSON or SSE streaming. The same Claude account
pool handles these requests. Chat `max_completion_tokens` (or `max_tokens`) and
`stop` apply to Claude output; unsupported controls return an error. Function tool
calls and tool results can be resent as ordinary Chat history. Claude reasoning
appears as plaintext `reasoning_content`; it is never treated as a signature.
When a keyed, complete tool follow-up uniquely matches a live same-key conversation
record, genuine signed thinking is replayed on its original account. Otherwise
the affected historical tool cycle is reconstructed from visible Chat content as
ordinary conversation, preserving supported results without claiming native tool
semantics or inventing a signature. New reasoning and tool requests remain enabled.
Use Responses or native Messages when exact native tool-continuation semantics matter.
Adaptive Claude requests ask for summarized thinking by default; use
`thinking: {"type": "adaptive", "display": "omitted"}` to hide it.
Haiku 4.5 and Sonnet 4.5 instead use budget-based thinking. Translated
low/medium/high/max efforts request 4,096/8,192/16,384/32,000 thinking tokens;
the output limit must exceed the budget and is never raised automatically.

## Model budgets

Clients receive a default context of the smaller of 272,000 tokens and discovered
capacity. Codex receives the true maximum separately, a 95% usable-context hint
and a 90% default auto-compaction threshold. A 1M-capacity Opus therefore defaults
to 258,400 usable tokens and 244,800-token compaction; a 200K Haiku keeps its
190,000 usable and 180,000 compaction budgets. This working default is aligned
with Codex, not a measured Claude quality limit. Account discovery still shows
the true provider capacity; output ceilings and explicit budgets are unchanged.

Translated requests without an output budget use the smaller of 64,000 tokens and
the model's maximum output. Explicit native or translated budgets remain accepted
up to that maximum. A 128,000-token output capability therefore does not force every
request to reserve 128,000 tokens.

Claude compaction sends complete materialized text, tool results and images to
the summarizer; it does not inherit native OpenAI's 100k compact wire trim.
The provider enforces actual capacity, not the conservative client default.
Oversized requests or incomplete summaries return an error without a checkpoint
or replacement of the original retained history. Signed Claude history must
remain on its original account/model; unavailable or conflicting owners and
signature rejection fail rather than silently removing reasoning. A short
summary alone does not indicate failed compaction. See
[source compaction safety](../openspec/specs/model-source-routing/spec.md#requirement-source-compaction-history-safety).

Request details show cache reads and cache writes separately when Claude reports
them, along with total duration, first generated-content latency and upstream
thinking mode. Upstream thinking mode and effort are shown only when codex-lb sent
them; a request that leaves them to Claude's model-dependent default shows neither.
Costs are API-equivalent estimates, not Claude subscription
charges. Missing prices appear as unknown (`--`), while token counts remain
visible. Historical logs without cache-write or timing detail are not inferred.

Upgrading preserves selected model IDs and removes former manual budgets.
Existing projections stay disabled until a successful catalog refresh resolves
their limits. Discovery errors remain visible; no guessed generic limits are used.

## Operate and recover

Model-specific Opus/Sonnet weekly rows appear only when
reported after a successful usage refresh; missing rows do not imply unlimited
quota or unavailable models. Known stale observations remain visible.

Pause/resume, quota monitoring, model selection and reconnect are in the shared
account detail. **Models** opens the searchable selection dialog; provider
capacity and CLI-version controls are under **Provider settings**. See
[shared model controls](../openspec/specs/account-model-controls/spec.md).
Routing policy offers Normal, Burn first and Preserve within the
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

Codex delegation or imported history can contain tool output without its call.
Responses preserves this as labeled user context, including supported images;
it does not fabricate a tool call or result. A real continuation still restores
its call from retained history. Duplicate paired results, results preceding
their calls, and interrupted or incomplete tool cycles fail before dispatch.
Native `/v1/messages` is unchanged. See
[standalone tool context](../openspec/specs/claude-accounts/spec.md#requirement-portable-standalone-tool-output-context).

Codex external task envelopes are a separate case: a `function_call_output`
with omitted/null/blank `call_id`, complete `id`/`name`/`namespace` metadata and
valid nonblank text/image output is ordinary user input, not a tool result.
Responses preserves its entire content without an orphan label and retains the
original envelope for replay. It counts as a new user turn for completed thinking,
but cannot interrupt pending calls or relax search-resource ownership. Malformed
or incomplete envelopes still fail. See
[external task input](../openspec/specs/claude-accounts/spec.md#requirement-canonical-codex-external-task-input).

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

## Codex function-tool schemas

Root `oneOf`, `anyOf`, and `allOf` declarations are adapted automatically for
Claude without merging away their constraints. The upstream request uses a private
`arguments` wrapper; Codex sees the original tool arguments and result pairing.
Wrapped arguments arrive as one validated delta at tool completion rather than
incrementally. Ordinary tools and native `/v1/messages` schemas are unchanged.

Unrelocatable references or excessive schema complexity return a named tool error
before dispatch. Invalid generated arguments fail the response, never complete a
tool call successfully. This is specified in
[Claude accounts](../openspec/specs/claude-accounts/spec.md#requirement-faithful-translated-claude-tool-schemas).
Mock HTTP/WebSocket tests cover the roundtrip; live upstream acceptance is separate
qualification.
