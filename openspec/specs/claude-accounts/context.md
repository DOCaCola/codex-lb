# Native Claude implementation notes

## Qualification

This implementation is locally verified with synthetic credentials, mocked
provider metadata and loopback HTTP/SSE servers. It is not a live Anthropic OAuth
acceptance or subscription-billing certification. It does not authorize extra
usage, conceal eligibility errors, execute Claude Code, or provide paid fallback.

## Enrollment and recovery

The shared Add account dialog offers OAuth PKCE or explicit credential-file upload.
No server-local credential files are inspected. The operator acknowledges exclusive
refresh ownership. Fresh enrollment verifies `/api/oauth/profile`; a hash of the
authenticated account/organization tuple uniquely identifies the account without
exposing profile identifiers in the dashboard. Expired imports remain unverified
until durable refresh and profile verification succeed. Refresh intent is committed
before sending a rotating grant. An uncertain result is not retried automatically.

Reconnect accepts OAuth or a current credential file for the same verified identity.
It increments the credential generation and clears old refresh intent/backoff.
Late refresh completions cannot overwrite it. An unverified account that cannot
refresh must be removed and enrolled again rather than guessed to be the same user.

## Transport and ownership

Native `/v1/messages` and `/v1/messages/count_tokens` use Claude-owned authentication.
Recognized Claude Code preserves native system layout and extension fields; native
recognition is only a compatibility hint. Third-party Messages and Responses use
the explicitly versioned OAuth identity/instruction profile. Caller authorization
is replaced; allowlisted protocol metadata is retained and redirects are disabled.

Responses uses the shared admission/reservation/settlement owner over HTTP and
downstream WebSocket; Anthropic upstream is HTTPS/SSE. Pings preserve liveness, EOF
without a terminal event fails, and pause/max-token stops remain incomplete. Native
streams retain Messages event names and bytes while a separate observer meters them.
Chat Completions for Claude models passes through the same Responses owner and upstream
Messages transport. The source's `supports_chat_completions` flag remains false because
it describes an upstream wire, while downstream Chat adaptation is selected by routing.
Usage includes uncached input, cache reads and cache creation; cache creation is
included in total input and exposed separately in Responses usage details. Ledger
costs use API-equivalent rates in the existing pricing catalog, not subscription
charges. Cache writes are priced separately when Claude reports 5-minute or
one-hour detail. Unknown TTL or unavailable rates leave cost unknown, not free.
Older rows are not inferred. For example, 170 input tokens comprising 100
uncached, 40 cache reads and 30 cache writes are logged as 170 total with
separate 40/30 details, and each category is priced once.

Portable text, images and function/free-form custom tool histories are projected.
Client tools are sent under Claude Code-shaped names (OmniRoute's mapping, e.g.
`terminal` → `Bash`, otherwise PascalCase), with namespaces qualified as
CLIProxyAPI does, and a request-local table restores the client identity. Opaque
hashed names were dropped because Claude then called the names the instructions
mention, and plain snake_case agent tool names are fingerprinted on OAuth
(OmniRoute PR #2943). Signed thinking stays in
encrypted account/model/client-bound envelopes, never fabricated
reasoning summaries. JSON-schema output and model-specific adaptive or budget reasoning use explicit model
policies; unknown model minors do not inherit capabilities optimistically. Grammar-format
custom tools (Codex's freeform apply_patch) become one raw-text input documenting the
grammar, because Anthropic cannot constrain decoding; Codex parses the input and returns
violations to the model as tool errors. Files, built-in server tools other than web
search, verbosity, automatic truncation and paid service tiers have explicit unsupported errors.
Native Messages may carry native extensions without pretending they are Responses
features. Switching models with signed state requires portable context.

Responses continuation uses the existing encrypted disk replay store (one-hour
retention). Complete and incomplete Claude output is saved before terminal delivery.
Compaction uses the selected Claude account for summary generation and the existing
encrypted compaction envelope for portable summary restoration. Native Messages
retains scoped resource identifier hashes/account/expiry, not conversation text.
Resource provenance slides for thirty days independently of one-hour soft
affinity. Missing resource origins fail closed.

## Monitoring and UI

### Billing-first native cache prefixes

Native recognition also accepts a leading `x-anthropic-billing-header:` block
under the existing qualifying Claude CLI software and OAuth headers. The marker
alone does not authenticate a client or select a native profile. Recognized
system blocks, cache markers and billing text remain in their original order;
the gateway neither moves nor stabilizes volatile billing metadata.

Agent LB commit `3eb7c18454a805a297ce22c92eeab73da225628f` (2026-09-25),
inspected at `c7f83276e4c8af0d7735adb6524fc68d34a97732` on 2026-10-01,
reports helper/teammate cache misses after prepending identity ahead of billing
metadata. This is third-party before/after evidence, not independently verified
live cache behavior. Native main/helper dispatch mocks verify layout preservation.
Measured cache monitoring is documented in `../provider-observability/`.

Accounts appear in shared dashboard cards/table, account selection, and Add account.
Controls include pause/resume, refresh, reconnect, selected models, context/output
caps and the global advertised-version pin. Privacy blur and read-only permissions
apply. Missing quota windows show unknown; stale data is labeled, not reset to zero.
Enabled accounts trigger leader-owned quota refresh every three minutes, catalog refresh
every six hours, and stable version discovery at startup when stale/every 24 hours.
Pinning affects advertised CLI version, not SDK/runtime baselines or profile revision.

## References

### Wire policy revision 2

Native feature betas are retained (including future syntactically valid tokens);
thinking/output_config no longer activate additional native betas. Translated
requests add only the implemented feature betas: enabled/adaptive thinking,
explicit effort, structured output, or relocated mid-conversation instructions.

The gateway scopes the session header and structured JSON metadata.user_id
session_id together by selected source, client key scope and conversation. Parent
session IDs use the same mapping. Other metadata fields, including account_uuid,
are not rewritten or invented. The stored logical input is never modified. For
example, a caller's session S maps to one upstream UUID on source A/key K, but a
different UUID on source B or key L. Token refresh does not change this mapping.
Malformed/opaque user_id formats or conflicting header/body sessions fail before
credential refresh; legacy concatenated user IDs are not silently converted.

Native request IDs and SDK retry counts survive; the internal request ID remains
an independent attempt identifier. Reviewed helper/async, agent lineage and
request-class/compaction headers are preserved only for recognized native traffic.
Remote environment/protection headers are not broadly forwarded. Compression
remains owned by the HTTP client, not copied from the caller.

Count-token recognition does not require the main system identity. The supported
Haiku 4.5 probe/title shapes additionally require structured session/header
agreement and native software signals; unknown helper shapes are not optimistically
recognized. Messages defaults to a 600-second advertised SDK timeout; count_tokens
does not synthesize it. This header is client metadata, not the gateway's actual
upstream timeout setting.

Research revisions, histories, competing approaches and caveats are recorded in
the workspace-local `claude-integration-design.tmp.md` linked from AGENTS.md.
Portable upstream references are Sub2API, OpenCodex, OmniRoute and CLIProxyAPI in
AGENTS.md. Their observed compatibility techniques are reference evidence, not
dependencies or a guarantee that Anthropic accepts this gateway.

### Translated wire policy revision 3

Responses `web_search` and `web_search_preview` map to Anthropic
`web_search_20250305`. As explicitly selected from CLIProxyAPI's policy,
`external_web_access: false` omits that declaration and continues the request:
it provides neither cached search nor permission for live search. Other tools
remain available. Live search accepts allowed-domain filters, approximate location
and positive `max_uses`; unsupported options (including `search_context_size`)
and forced hosted-search choices fail explicitly before dispatch.

Search lifecycle and URL citations are projected into Responses. Exact upstream
server call/result blocks travel in authenticated `reasoning.encrypted_content`
alongside the public `web_search_call`; clients must retain both. The carrier
uses the existing account/model/client binding and durable replay
store. Missing or altered state and incompatible scope fail explicitly; no
encrypted result is fabricated from citations. Active-turn search keeps its owner
and model; completed search moving to another provider, model or account becomes
readable text (see "Cross-route history projection"). Search errors or
unfinished server calls cannot be reported as successful completion.

Translated requests stamp one-hour ephemeral cache boundaries (with beta
`extended-cache-ttl-2025-04-11`, as Claude Code sends) on the last system block
(or last tool if there is no system block), plus the last two cacheable
user-turn tails. Agent turns often pause past five minutes for tool work, so
the default tier rewrote the prefix after most such pauses (41/42 turns after
5–60 minute gaps, 2026-10-01). Native cache markers and signed server blocks
remain untouched. These are eligibility hints, not a guarantee of cache hits.

Synthesized metadata carries a stable local source/client device hash and the
same scoped session UUID as the header. `account_uuid` is empty: the stored
provider identity fingerprint cannot recover the actual UUID. Runtime OS and
architecture are advertised consistently. The observed browser-access header is
included; the unobserved stream-helper header is not synthesized (recognized
native caller values remain preserved). SDK/runtime versions remain reviewed
constants, separate from dynamically discovered Claude Code version.

CLIProxyAPI revision `ef9e712` was inspected on 2026-09-27 as a structural
reference, not copied source. The isolated bundled Codex app-server 0.157.1
completed cached-search text/tool/follow-up and live-search/citation/follow-up
tests against a synthetic Anthropic recorder. The latter verified exact encrypted
search result replay. This remains mock compatibility evidence, not live OAuth
acceptance or billing qualification.
# Native affinity and signature recovery

Native thinking and redacted thinking alone do not require an account-owner
record. Existing one-hour session affinity is soft; authorization and eligibility
win, and child sessions can prefer their scoped parent's account. Explicit session
headers and structured metadata must agree. Missing identity does not use content
hashes or shared prompt-cache cohorts.

A pre-delivery HTTP 400 explicitly rejecting a thinking signature may trigger one
same-target retry with completed historical thinking omitted. Active tool chains
stay unchanged; empty-message or server-tool histories refuse recovery. Normal
traffic is unchanged. No thinking-to-text, tool-to-text or synthetic redaction.
Count-tokens and errors after output never use this recovery.

Keyed Chat tool follow-ups locate signed thinking only from the bounded Responses
replay store. The complete canonical visible prefix, instructions and tool-call
set must match one live response under the same key, conversation, model and
account; plaintext `reasoning_content` is never promoted into a signature.
Missing, ambiguous, expired, cross-key and owner-unavailable records reconstruct
the affected tool cycle as ordinary assistant text and quoted user data. This
preserves representable visible content but does not preserve native tool-use
semantics. Unrepresentable media fails explicitly; search/resource state cannot
be reconstructed from Chat-visible history. Retained projected input and separate
canonical Chat input support matching on later turns without re-signing text.

After native account rebinding, observed resources resolve independently: old
resources still belong to the old account and new resources to their issuing
account. Mixed or unknown origins fail rather than borrowing session affinity.
Translated Responses envelopes and their ownership checks remain unchanged.

Reference evidence: OmniRoute PR #7906, OpenCodex native versus translated replay,
CLIProxyAPI parent affinity. These are source/mock checks, not live OAuth acceptance.

## Overload recovery

Explicit 529 and structured 503 overloaded_error refusals allow one same-account
retry within the shared four-send budget. This borrows bounded-wait policy lessons
from OpenCodex, early SSE classification from Sub2API, and the distinction between
model capacity and provider health from OmniRoute; it does not copy their broader
rotation or cooldown policies. For example, a ping followed by overloaded_error
can recover without publishing the failed attempt's response ID. An empty text
block followed by that same error cannot: generation has already started.

Startup inspection is bounded to 32 events, 64KiB, and the existing first-frame
deadline. It delays metadata delivery until generation or a terminal event;
malformed or unknown events end recovery eligibility. Retry waiting owns no
admission/reservation and observes client disconnects. Long Retry-After hints
return unchanged instead of exceeding the ten-second recovery window. These
paths are locally tested, not qualified against live OAuth traffic.

## Capacity-aware pool admission

Claude accounts reuse the existing source concurrency limit. The dashboard field
is optional: empty means unlimited; a positive integer applies per worker across
the account's models, not globally across replicas or as a claimed provider quota.
For example, portable history preferring a full account A can be reprepared for
available B. Active account-bound reasoning/search history on A cannot move.

Atomic admission, not a racy preflight counter, decides availability. Validation
and credential preparation still precede the claim; a typed local rejection sends
selection back through the normal authorized, ownership-aware preparation path.
Each rejected source is excluded once. This does not spend an inference-send
budget or cause quota/auth/health penalties. All-full pools return local busy
with a one-second retry hint; no new waiting queue is introduced.

Native affinity is saved after admission so rejected new candidates do not create
false resource-owner history. Concurrent incompatible ownership changes return
claude_session_changed before inference; the held slot is released. Existing
SourceDispatch owns admitted-request cleanup and settlement. This adapts Sub2API's
selection/admission integration and CLIProxyAPI's distinction between local busy
and provider failures, without adding their deployment-specific RPM/session caps.

### Passive inference quota observations

Physical Claude responses update five-hour and seven-day usage before reading the
body, including rejected attempts. Each sample belongs to its sending account and
credential generation. Request-start ordering chooses poll versus header evidence
per window; header receipt does not refresh unrelated windows or clear cooldowns.
An expired reset becomes unknown, not a fabricated zero. Generation/version-fenced
state merges preserve concurrent settings and poll changes. Header persistence is
best-effort with a 500ms deadline; cancellation retains upstream cleanup ownership.
History samples are throttled per account/window to once per minute.

Fractions above 1.0 remain valid: 1.04 is stored/displayed as 104% and blocks the
applicable window, while the remaining-quota bar is bounded at zero. There is no
alternate-scale guessing. Invalid or nonfinite converted percentages are ignored.
This differs from OpenCodex PRs 3809/3825's defensive upper bound: Sub2API commit
e681431454ab53a4d4fa0b8c6930497a14e5bdd0 tests overshoot and Dario issue 1244 reports
a physical 5h utilization of 1.04. CLIProxyAPI issues 5915/5920 report a separate
model-specific 1.02 window; they do not establish account-wide exhaustion. These
are third-party reports, not our own live capture, and the upstream cause of
overshoot is not established. Inspected snapshots: OpenCodex 3cc34e118192 and
Sub2API 9a62841fd124 (2026-09-28).

### Scoped overage refusals

Unified rejection can describe the requested model's overage claim while included
subscription windows remain healthy. Classify scope before assigning deadlines.
Explicit shared rejection still blocks the account; overage evidence plus healthy
shared windows blocks only the requested model. Allowed_warning is healthy.
An omitted status requires finite utilization below one and the other window
explicitly allowed; unknown is not healthy. Structured credits_required is model
entitlement evidence, not a reason to disable siblings. Fast-mode refusals retain
their separate no-failover policy.

Mixed failures persist both scopes atomically. For example, shared reset in two
hours and special-model reset in eighty hours must let siblings resume after two
hours while retaining the model restriction. Retry-After and aggregate reset are
assigned to the representative claim's scope, or the sole unambiguous scope.
Explicit scoped resets remain lower bounds even with shorter retry hints. Missing
attributable deadlines use the existing sixty-second default. No new spending
policy or model-family entitlement inference is introduced. Existing deadlines
only extend; historical ambiguous cooldowns are not automatically rewritten.

This adapts CLIProxyAPI acdace936fa7's conservative classification and integration
tests for issues 5915/5920, and Sub2API 9a62841fd124's independent shared/model
restrictions. CLIProxyAPI fix 1cce9325738f discards overage Retry-After to avoid
credential-wide backoff; here scope and deadline stay coupled, so model-only
deadlines can be retained. Sub2API fix 222181efd6be restricts credits_required
handling to Fable; our structured error applies to the requested model without
copying its family mapping. These are source/test adaptations, not live OAuth
qualification. No schema migration or operator setting is needed.

### Manual reset grants

The account dialog explicitly discovers cedar_ember grants and requires confirmation
before spending. Discovery failure is unknown, not zero availability. There is no
automatic redemption, failover or juniper_tide support. Existing management headers
and the runtime Claude Code version are reused.

A SQL journal persists intent before POST, bound to verified account/organization
identity and the selected grant. A 90-second lease prevents concurrent claims;
explicit same-ID retries are allowed for ten minutes with a 25-second POST timeout.
After uncertain expiry, a fresh operation needs separate risk acknowledgement and
fresh eligibility. Records survive deletion/re-enrollment and token rotation and
are retained without automatic pruning, so uncertainty is not silently forgotten.
They contain identifiers, timestamps and typed outcomes, not credentials or prompts.

Settlement and selective reconciliation commit atomically. The barrier is the
original intent timestamp, not a retry timestamp: a retry can replay an earlier
successful reset. For example, a five-hour refusal observed between a lost reset
reply and its successful retry must survive that retry. Concurrent, unknown legacy,
entitlement and uncleared-window restrictions also survive. Cleared usage is unknown
until freshly observed; polling failure never changes a settled redemption result.
The migration adds typed cooldown evidence and the operation journal. Historical
cooldowns with no evidence remain unknown restrictions until normal expiry.

Adapted protocol/safety lessons from OpenCodex 3cc34e118192, merged PR5632
(2026-09-23), reviewed 2026-09-28. Its post-expiry fresh-ID policy accepts a
double-spend risk; this UI requires explicit acknowledgement. OmniRoute a58000c7685f
PR13074 implements a different program, while PR14728 was still an open proposal.
No reference source was copied. Local mocked protocol, migration, concurrency and
dashboard tests do not establish live OAuth redemption or billing acceptance;
PostgreSQL runtime qualification remains outstanding.

### Pool exhaustion and retry hints

Quota-only exhaustion returns429 with rate_limit_error, while mixed/unknown
unavailability retains503. Paused, model-disabled and credential-invalid accounts
cannot contribute a recovery estimate. Account recovery includes all quota and
cooldown barriers; unknown quota deadlines suppress that account's estimate.
For example, shared reset2h plus model cooldown5h cannot advertise2h; an eligible
sibling resetting3h gives the pool a known3h estimate. Hard owners never borrow
a sibling's deadline. Explicit upstream failures after dispatch remain unchanged.

This adapts CLIProxyAPI's typed cooldown distinction and OpenCodex's earliest
cooldown hint without copying their source or unscoped account scans.
The source WS bridge preserves Retry-After, but older Codex clients may still
treat429 as terminal. Header delivery alone does not guarantee automatic resume.

### Native resource provenance

Native server-tool identifiers are scoped by client/model and
stored as hashes with source and timestamps. The one-hour affinity record is
only a cache preference. Thirty-day sliding provenance is an operator-facing
retention policy, not a guarantee of upstream resource validity. Cleanup deletes
at most 500 expired rows per resource-bearing output transaction. No prompts,
tool arguments, results or complete conversations are stored in this ledger.

Origins commit before their first identifying SSE frame or JSON response.
Persistence failure stops delivery without replaying generation; committed but
undelivered entries expire normally. Authorized admitted replay refreshes
retention; count_tokens is read-only. Token rotation leaves provenance intact.
Deleting a source cascades its origins; re-enrollment does not guess old owners.

For example, A issues R1 and a portable branch later moves to B and obtains R2.
R1-only history routes to A and R2-only to B even after cache affinity expires.
History containing both fails. Temporary owner failures keep existing scoped
retry hints. Permanent loss still needs explicit portable context.

There is no reliable backfill from legacy affinity rows. Pre-upgrade resource
history may require portable context. Files/containers need separate endpoint
and origin-capture support and are rejected explicitly, not assigned by guess.
Translated authenticated reasoning/search replay remains unchanged.

This is a local provenance design informed by the affinity/preservation lessons
from the four AGENTS.md references, not copied resource-migration machinery.
Mock verification does not establish live cross-account resource portability.

## Shared routing policy

Claude reuses the selected routing strategy, earlier-reset preference and
relative-availability tuning, but never the OpenAI account pool or plan-capacity
estimates. Every Claude candidate supplies one normalized capacity unit. Fresh
five-hour usage maps to primary pressure; the most utilized fresh applicable
weekly window supplies secondary pressure and its reset time. Quota strategies
prefer the cohort with fresh shared five-hour and weekly readings. With no such
cohort, eligible accounts rank neutrally; unknown usage remains unknown in storage
and presentation. Existing stale-exhaustion exclusion still applies.

Eligible durable affinity stabilizes admitted native and translated conversations.
Hard resource owners remain mandatory. Independent provider-specific single-account
targets fail explicitly when missing, unavailable or conflicting with ownership.
OpenRouter routing is unchanged. Round-robin uses durable admission recency as a
hint, not an atomic cross-worker scheduling lock; existing concurrency admission
remains authoritative. RPM/session caps and automatic Claude plan multipliers are
not part of this policy.

## Automatic model capabilities and account parity (2026-09-29)

Successfully retained usage determines optional model-specific windows. A Pro
snapshot reporting only five-hour and shared weekly usage omits the unreported
Opus/Sonnet rows, rather than displaying misleading unknown percentages. This
does not establish unlimited access or model entitlement. Before successful
discovery, genuinely unknown rows remain; known scoped samples remain visible
when stale or temporarily invalidated by a reset barrier.

Authenticated read-only Models API discovery on the connected account returned
HTTP 200 with token limits on every listed model, including Opus 5 at
1,000,000 input / 128,000 output and Haiku 4.5 at 200,000 / 64,000.
This establishes that account's catalog response, not generation quality or
every account's entitlement. No inference or token refresh was performed.

Discovery fields win; explicitly maintained known-model entries fill absent
fields. Unknown incomplete models stay unavailable. Selection stores identifiers
only. The migration removes old manual fields, invalidates catalog freshness,
and disables old projections until refresh. Downgrade drops routing policy but
does not recreate discarded operator limits. The existing scheduler refreshes
invalidated catalogs; a failed refresh remains visible.

A model ceiling and a default request budget are different contracts. The
translated default is min(64,000, output maximum); valid explicit budgets survive.
Client metadata now separates the default working context from true capacity:
min(272000, capacity), 90% default auto-compaction and 95% effective context.
Opus at 1M advertises 272000 default / 1000000 maximum, with 244800 compaction
and 258400 usable tokens. Smaller 200k models remain at 200k. The 272k default
is the operator-approved policy aligned with the local Codex catalog; neither
threshold is a Claude quality benchmark. Discovered capabilities remain intact
in account state and model-source storage. Derivation at catalog construction
also updates existing projections without waiting for discovery. No arbitrary
350k cap or provider-specific token editor is retained. Existing global context
overrides remain an operator-level control through the shared catalog path.

Historical evidence (source/comments inspected at the following revisions):

- OpenCodex `8a005dd98`: [#3332](https://github.com/lidge-jun/opencodex/pull/3332)
  reported 8k truncation and five client retries; its author's 9,344-token answer
  succeeded. The change shipped in
  [#3474](https://github.com/lidge-jun/opencodex/pull/3474),
  commit `00834d710` (2026-09-04), using a 64k provider default.
  This is a practical truncation report, not evidence that 64k is universally optimal.
- OpenCodex [#1905](https://github.com/lidge-jun/opencodex/pull/1905),
  commit `d659c542f` (2026-08-25), separates lowering-only soft compaction
  budgets from true context bounds. Its older 350k option was provider-generic,
  not a measured Claude limit.
- Sub2API `9a62841`: commit `a25faecad` (2026-04-24),
  [#1914](https://github.com/Wei-Shaw/sub2api/pull/1914), filled missing
  max_tokens with 128k to match then-observed CLI traffic. Our isolated Claude
  Code 2.1.283 capture used 32k, so one observed CLI default is not universal.
- CLIProxyAPI `d33f63f`:
  [#3833](https://github.com/router-for-me/CLIProxyAPI/issues/3833)
  reported missing token-limit fields breaking client interoperability.
- OmniRoute `c3c540da`:
  [#14827](https://github.com/diegosouzapw/OmniRoute/pull/14827)
  preserves authenticated discovery limits/pagination (merged 2026-09-29;
  reported 12 discovered models and a generation test).
  These are third-party observations, not independently repeated live generation.

Claude quota bars, list cells, credential rows, pause button and routing selector
reuse Codex components. Unknown/stale/over-quota observations remain explicit.
No OpenAI workspace, subscription-credit or warm-up state is invented for Claude.
Normal/burn-first/preserve is stored per Claude account and supplied to the existing
shared candidate; hard owners, eligible affinity and strategy-specific exceptions
remain unchanged.

## Metadata endpoint backoff (2026-09-29)

Usage and model catalog requests have separate persisted claims/cooldowns in
account state. The leader ticks every minute, but successful usage is cached for
three minutes and catalog for six hours. Manual refresh bypasses successful-cache
cadence only. Concurrent callers reuse retained state; a caller does not repeat
an endpoint another worker completed since that caller began.

A logical fetch is bounded to 60 seconds with a 90-second durable lease.
Completion requires both the owning operation UUID and credential generation.
Claims commit before network I/O; successful projection/history commits with
state. Cancellation or process loss leaves a lease that expires, not an unsafe
authentication retry. Settings and newer inference observations merge independently.

HTTP failures identify the endpoint/status and next retry deadline. Retry-After
seconds and HTTP dates are honored; absent or malformed hints use three minutes.
Other metadata failures also cool down for three minutes. On expiry a failed
endpoint becomes due even if its last successful reading is within normal cadence.
For example, usage HTTP 429 with Retry-After: 600 leaves the last readings/timestamps intact,
marks poll data stale and blocks both manual and scheduled usage calls for ten
minutes. Catalog and inference continue independently. Newer inference headers
can refresh their own quota windows without clearing the polling error.

This applies to scheduled/manual usage and catalog reads, not rotating OAuth token
exchanges or grant redemption. Profile enrollment uses endpoint-specific errors,
but is not a scheduled poll and has no account-level metadata claim before enrollment.
No metadata failure pauses an account or causes an inference-health penalty or
reactive token refresh. Normal expiry-based credential refresh remains unchanged.

Reference evidence inspected 2026-09-29: Sub2API `9a62841fd` uses three-minute caching,
singleflight and short jitter (history `3ebebef95` documents 429 stampedes);
OpenCodex `8a005dd98` coalesces probes and negatively caches preserved readings;
OmniRoute `113de57b` separates usage throttling from Messages with a three-minute
cooldown. CLIProxyAPI `d33f63f8` had no equivalent core OAuth usage poller.
Durable cross-worker claims and honoring Retry-After are our additions.
No legacy endpoint fallback or third-party source was copied. Mock tests establish
local coordination/protocol behavior, not universal live Anthropic limits.

## Translated tool-schema adaptation

Anthropic rejects root oneOf/anyOf/allOf on function input_schema. Responses
tools using those keywords or a root local reference receive an upstream-only
object with one required `arguments` property containing the original schema.
For example, mode-specific view/id and update/prompt alternatives keep their
required fields and closed-object constraints. Claude returns
`{"arguments":{"mode":"view","id":"item"}}`; Codex receives only
`{"mode":"view","id":"item"}`. Ordinary schemas and native Messages
tools retain their existing representation.

Local JSON-pointer references move with the schema. Unsupported reference scopes
are named client errors, not relaxed schemas or dropped tools. Adaptation is
bounded to 64 levels/4096 visited nodes and wrapped arguments to 2 MiB UTF-8.
Wrapped deltas are buffered until complete, parsed and validated against the
original schema before publishing executable arguments. Failure terminates the
response without successful tool completion. Logical replay stores original
arguments; each attempt encodes history using its current declaration.

Reference inspection on 2026-09-29: OpenCodex `8a005dd98` (PR76, cherry-pick
`070839a64`), CLIProxyAPI `d33f63f8` (issue4428, fix `59aa35a4`), OmniRoute
`113de57b` (PR13561), Sub2API `9a62841fd` (PR7345). Sub2API's report reproduces
Codex desktop automation_update rejection and success after normalization.
These Claude normalizers merge branches lossily: our OpenCodex/OmniRoute probes
showed lost valid modes and accepted invalid arguments; Sub2API retains property
alternatives but loses cross-field requirements. The reversible envelope avoids
that loss. No third-party source was copied.

HTTP/WS mock roundtrips verify declaration, fragmented arguments, result pairing,
continuation and cleanup. Third-party nested-schema acceptance informs this
design but does not establish live acceptance of our exact envelope. Production
qualification still requires a real Claude tool request. Chat Completions routing
to Claude is a separate gap and is not added by this change.

## Standalone Codex tool-output context

The 2026-09-29 production logs show two locally generated "No matching Claude
tool call for this output" errors, before Anthropic dispatch. The last successful
Opus history retained complete call/result pairs; the failed input was not stored,
so its exact cause cannot be established retrospectively. A standalone delegation
seed reproduces the same rejection in the deployed projector.

Inspected 2026-09-29 snapshots: CLIProxyAPI `d33f63f8` explicitly tests Codex
create_thread seeds with unmatched function_call_output; it converts these into
ordinary user content. OpenCodex `8a005dd98` labels orphan tool results and retains
text/images without fabricating calls. These are source/test observations, not
live qualification of our route. No reference implementation was copied.

Our projector classifies against the entire expanded input. A result whose call
appears later is out of order, not standalone context. A second result for a
consumed real call is a duplicate, not portable context. A standalone output with
no call becomes labeled user content only outside an unresolved tool cycle. For
example, a delegation seed and user instruction become one user message containing
the original output and instruction, with an explicit standalone-output label.
Text and supported images remain intact; no tool execution or signature is implied.

Existing previous_response_id expansion still occurs first. An unavailable
explicit previous response still fails, rather than reclassifying its delta as
context. Signed reasoning and resource ownership checks remain unchanged. Native
Messages bypasses this policy. Logical replay retains original output items rather
than the projected labels, avoiding label duplication on later turns.

Rejected output diagnostics record reason, item position/kind, request ID, pending
count and the first 12 hex characters of the call-ID SHA-256. They never record
output, arguments, images, raw call IDs or credentials. There is no per-item success
logging. Local HTTP/WS mocks cover context, continuation and strict failure paths;
live OAuth acceptance is a separate qualification step.

### Canonical external task envelopes

A subsequent production rejection at 2026-09-29T21:10:15Z had reason
invalid_call_id, item_index=38, call_id_hash=None and pending_count=0. This confirms
a missing/null/non-string identifier reached our guard; the metadata shape was
not captured, so the precise failed envelope is not retrospectively established.
The previous fix was incomplete: not all function_call_output history items are
paired results. Current Codex ResponseItem allows optional call_id/name/namespace.

OpenCodex issue #3807 (reported September 6, closed by merged #4058 September 8 UTC)
documents Codex desktop sub-agent envelopes with id/name/namespace/output and
omitted/null/blank call_id, including later occurrences within existing history.
Inspected revision 8a005dd98 has an explicit complete-envelope classifier in
src/responses/task-input.ts plus initial/established-history tests. It lowers
these items as ordinary user input, distinct from labeled generic orphan results.
CLIProxyAPI d33f63f8 converts ID-less/unmatched outputs more broadly. Sub2API
9a62841fd drops orphan tool_results during pairing normalization; OmniRoute
113de57b filters orphan outputs on Responses-to-Chat. Those data-dropping or
heuristic pairing approaches are not adopted. These are source/test/report
observations, not independent live verification.

Our shared task classifier requires nonblank string id/name/namespace, no usable
pairing key (omitted/null/blank string), and nonblank supported text/image output.
Wrong-typed keys, incomplete envelopes and unknown blocks are not repaired.
For example, {type: function_call_output, id: fc_seed, name: create_thread,
namespace: codex, call_id: null, output: "Continue the delegated task"} becomes
ordinary user text without a fake call or orphan label. All blocks stay ordered;
Claude's existing image media/transport validation still applies. Original
logical items remain retained, so later replay repeats neither labels nor roles.

Canonical tasks count as new user turns for completed-thinking replay policy.
All opaque blocks are still authenticated, active tool cycles cannot be
interrupted, and active server search/resource history remains owner/model-bound.
Logs add identifier presence/type and task-metadata completeness only; they do
not expose metadata values, content or credentials. HTTP/WS and retained genuine
tool-continuation mocks exercise this behavior; live acceptance is unverified.

## Switching Claude history to native Codex

The native Codex boundary cannot resolve Claude's `resp_msg_…` reasoning IDs or
decode our authenticated `claude-v1.` envelopes. Renaming an ID would conceal
only the first incompatibility. Native dispatch now authenticates the envelope
against the same client scope used by source retention and then omits Claude
thinking from the outbound projection, never from retained history. Ordinary
messages and function/custom-tool call/result pairs retain their contents and
call IDs.

Thinking used to become a summary-only `reasoning` item. OpenAI accepted that
as fresh input, but stored it as "unverifiable hidden reasoning" and rejected
the next turn chained onto it with `previous_response_id`
(`unsupported_persisted_item_context`). CLIProxyAPI, sub2api and OmniRoute all
forward reasoning to OpenAI only as genuine provider ciphertext, so the native
boundary now drops every reasoning item without `encrypted_content`, including
plaintext reasoning from OpenRouter models. The native model loses the other
provider's private reasoning, not anything the user saw; switching back replays
the retained originals. Logs count `thinking_omitted` and
`unverifiable_omitted`, never content.

## Cross-route history projection

Codex multi-agent v2 forks children with the parent's full history, so a child
on another provider replays state it cannot read. Unrepresentable provider state
is translated rather than rejected:

- Redacted thinking has no readable content and is omitted toward OpenAI, as it
  already is toward another Claude model.
- Hosted search toward another provider, and completed Claude search toward
  another Claude model or account, becomes one assistant `output_text` message at
  the call's position: `Web search: <query>` (or `Opened page: <url>`,
  `Found in page <url>: <pattern>`), then `Sources:` with `- <title> — <url>`
  lines. Claude results supply title/URL; OpenAI results use `action.sources`
  when the client kept it, otherwise the query alone.
- Active-turn Claude search between Claude routes keeps its owner and model.
  A search envelope without its matching `web_search_call` is invalid history.

The rendering is deterministic, so the moved prefix stays cacheable, and retained
history keeps the originals, so returning to the original route replays natively.
Logs count omitted thinking and `search_projected`, never content.

References (inspected 2026-10-06): CLIProxyAPI `a2976eb` drops redacted thinking
toward foreign upstreams and folds a Claude search pair into a structured
`web_search_call` with a minted `ws_<srvtoolu>` ID; opencodex `beba8b7` drops
`redacted_thinking`, strips signatures and keeps search text plus URL/title
sources (an opt-in `enforce` mode refuses lossy translation); Sub2API drops
redacted thinking and carries search only through the answer text. We use text
instead of a structured call because the native boundary never fabricates
foreign identities, a Claude call has no `ws_` ID, and acceptance of ID-less
`web_search_call` input cannot be established without live probes; assistant
text is accepted by both providers and carries the content the references keep.
No fake signatures, search calls or server-resource ownership are created.
Malformed/cross-client/cross-conversation envelopes fail before dispatch. Native
opaque reasoning stays encrypted and is not decoded or re-encrypted by the proxy.
HTTP, WebSocket, retained continuation and compaction share this policy. Logs
record a conversion count only. The low-level native transport rejects envelopes
that bypass authenticated preparation.

Inspected on 2026-09-30: OpenCodex
`569e3e7dae48bafc54b8a1a7e3a85129befe2d98` removes invalid type-specific item IDs
and route-incompatible reasoning; CLIProxyAPI
`a270e7b9e57aaecd8f82555f44c2108518ad2330` validates native blob format and
promotes plaintext reasoning into summaries; Sub2API
`42bc7f6cffe24bcb471608e48e66b4a0afa1f882` removes Codex reasoning lookup IDs
and recovers from invalid ciphertext; OmniRoute
`fc5e2bccd4f70fecf5aab94dfb8136c74ab5a21b` has transport compatibility and
replay-rejection policies. These are source/test observations, not live
acceptance guarantees. Our extraction/rejection policy intentionally avoids
blanket foreign-ciphertext deletion. Local authenticated endpoint and serializer
tests verify projection, rejection and unchanged retained state; production was
not changed during implementation.

## Switching native Codex history to Claude

The opposite direction needs provider classification before Claude authentication.
Native OpenAI ciphertext is not a `claude-v1.` envelope. Completed foreign
reasoning with readable summaries or reasoning_text is projected as ordinary
historical assistant text, preserving distinct channels and omitting ciphertext
and lookup identities only from the wire representation. Original retained items,
messages and tool pairs remain unchanged. For example, Sol reasoning followed by
a new user request becomes assistant text when that request selects Opus 5.5.
Explicit users and canonical external tasks close historical turns; paired tool
results do not. Empty plaintext reasoning retains its item position for errors.

Completed opaque-only foreign history produces no Claude wire block but remains
unchanged in retained logical history. Its temporary projection keeps an empty
plaintext reasoning item so later diagnostics retain their input indices. The
existing protocol renderer emits no block for that item. The active turn,
including an open tool loop, is projected the same way. Compaction applies the
same projection to the client-supplied history, with the appended summarization
instruction split off structurally. The active-turn boundary still matters for
genuine Claude envelopes and for the `active=` count in the projection log: a
history ending with an assistant message is a closed turn; otherwise the last
user or task input starts the active turn. Codex records interrupts as a
`<turn_aborted>` user message, so interrupted turns are closed too.
Plaintext-only compaction preserves readable reasoning.

Active foreign ciphertext was refused until 2026-10-03. Thread `01a0f38a`
switched from Sol to Opus 5.5 at 00:12:48 UTC directly after a Sol tool call
and failed with `nonportable_provider_history`; it could only continue on Sol.
Claude can never use that ciphertext, so refusing preserved nothing. OpenCodex
`249462bf5`, CLIProxyAPI `2044a01f4`, OmniRoute `23a114848` and Sub2API
`b8dece900` (inspected 2026-10-03) drop foreign reasoning regardless of the
active turn; none refuses the request. Anthropic's adaptive thinking, used by
Opus 5.5 and Sonnet 5.5, does not require an assistant turn to start with a
thinking block.

An earlier rule rejected all foreign ciphertext during compaction, because a
display summary cannot prove the full encrypted state survived. Production on
2026-10-01 (14:20–14:22 Berlin) showed the cost: an Opus turn projected 66
opaque-only Sol items successfully, then auto compaction on the same history was
refused and the user had to switch back to Sol. A Claude summary can only cover
what Claude can read, which is also all that every normal Opus turn uses. Failed
compaction still leaves the original history unchanged. OpenCodex `ef0297f`,
Sub2API `d6adebd`, CLIProxyAPI `fd48ea6` and OmniRoute `dbe703a0` (inspected
2026-10-01) all drop foreign opaque reasoning; none refuses compaction for it.
Genuine Claude envelopes, including empty-display signed thinking,
retain client authentication and account/model ownership. Invalid
authentication returns `invalid_provider_history` rather than a generic payload
error. Conversion logs contain only conversion and opaque-omission counts.

The first implementation unnecessarily rejected completed opaque-only items.
Production at 2026-09-30T16:23:45Z exposed that real inherited OpenAI history has
empty-summary ciphertext alongside portable messages and tools. The revised
policy preserves that visible conversation, not an unavailable private chain
of thought. Retained native state is not deleted. CLIProxyAPI's inspected
Responses-to-Claude converter omits foreign signatures instead of replaying
unsigned thinking; our projection additionally retains readable summaries as
ordinary text.

Inspected on 2026-09-30: OpenCodex
`569e3e7dae48bafc54b8a1a7e3a85129befe2d98`, CLIProxyAPI
`a270e7b9e57aaecd8f82555f44c2108518ad2330`, Sub2API
`42bc7f6cffe24bcb471608e48e66b4a0afa1f882`, and OmniRoute
`0b62441dbcc3f86a1844a77558733b806537e688`. OmniRoute #6953/#12105 and
merged #12386 show why unsigned thinking must not be forwarded or given fake
signatures. CLIProxyAPI #3663's September 21 follow-up warns that genuine signed
thinking can have empty displayed text; its unmerged #5497 thinking downgrade is
not adopted. OpenCodex's September 28 merged #6217 reports Opus 5.5 rejects a
thinking off-switch, while #4769's replay guard supports explicit failure for
unavailable mandatory state. Sub2API #5329 concerns malformed translated replay,
not independent native OAuth qualification. Unlike blanket foreign-reasoning
deletion in reference adapters, this policy preserves readable context.
Endpoint mocks verify the transformation and refusal contracts, not live OAuth
eligibility or full encrypted-state portability.

## Automatic subscription labels (2026-10-01)

Claude plan metadata is separate from encrypted rotating credentials and quota
evidence. Credential imports preserve subscriptionType/rateLimitTier; authenticated
bootstrap supplies organization_type/organization_rate_limit_tier. Known exact
identifiers resolve to Free, Pro, Max, Max 5×, Max 20×, Team or Enterprise. A generic
Max stays generic; absent or unfamiliar metadata is Unknown. Plan labels do not
set capacities, model eligibility, pricing or included-usage guarantees.

For example, an imported Pro account can become Max 20× when bootstrap reports
default_claude_max_20x. The ordinary scheduler discovers existing accounts without
reimport, checking successful subscription observations every six hours. Manual
refresh can bypass that cadence, not failed-attempt cooldowns or active claims.
The independent endpoint uses the existing 60-second timeout, 90-second lease,
Retry-After handling and credential-generation fencing. Its account/organization
fingerprint must match enrollment. Failures preserve the observation and show a
safe diagnostic, without changing inference health or blocking the other metadata
endpoints. Reconnect preserves last-known data unless an explicit import supplies
new metadata, then schedules rediscovery. Token rotation does not discard it.

Cards, lists and details reuse existing provider/account styling with localized
plan labels. Prepared attempts snapshot the normalized plan after final account
validation, before dispatch; SourceDispatch retains it for completion, errors,
native token counting and downstream WebSockets. Retries snapshot their own
selected accounts. A request prepared on Pro stays Pro even if metadata changes
during inference. Historical rows without a snapshot are not relabeled from the
current account. No migration, manual plan editor or inference-time bootstrap is
needed.

Reference source inspected 2026-10-01: OmniRoute
`dbe703a0000b303cd7b1cf5879cb8740e5bfce71`, live bootstrap in
open-sse/executors/claudeIdentity.ts, credential import and ProviderLimits/utils.tsx.
Its live bootstrap reads oauth_account; a separate enrollment parser has a
different shape, so alternate payload guesses are not adopted. Our implementation
adds account/organization validation and durable polling using existing gateway
machinery; no third-party source was copied. Mock protocol, race, persistence,
request-log and browser tests verify local behavior, not live acceptance or Free
account OAuth eligibility.

## Gateway throughput estimates

Claude's reported output includes thinking, while a separate reasoning count may
be unavailable. TPS therefore uses inclusive output rather than claiming a
visible-text decode rate. The proxy can observe delivery, not upstream generation
start. Nonempty redacted thinking and signatures prove opaque output arrived and
anchor TTFT before protocol adaptation; they do not establish a token count.

Successful turns need at least one second after first output to yield estimated
TPS. For example, 578 tokens with 6713 ms total and 6690 ms TTFT has only 23 ms of
observation: TPS is unavailable, not 25,130.4. The original timings, tokens and
costs remain available. Reports and conversation analytics exclude the same
sample. No timing clamp, full-duration substitution or historical rewrite is
performed. Longer windows can still reflect buffering; the estimate marker and
tooltips communicate this limit. Native OpenAI metric semantics are unchanged.

Reference inspected October 1, 2026: OpenCodex
`ef0297f86c4540c7d757c8595170d66f9c584aec`,
`src/server/management/shared.ts`: estimated post-TTFT throughput with a one-second
floor. CLIProxyAPI `fd48ea6840f5572deb53aeb5657740937ac9daaa`,
`internal/runtime/executor/helps/claude_ttft_helpers.go`: signature output
recognition. No third-party code is copied. Mock tests establish gateway metric
behavior, not the reason a particular live upstream delivered in a burst.

## Quota-blocked continuation owners (2026-10-01)

A signed active tool turn or hosted resource can require its original Claude
account even when another account is available. Exhausted quota is not a
connectivity failure: pure quota exclusion returns 429 rate_limit_error while
retaining previous_response_owner_unavailable and the account scope. Paused,
unauthorized, refreshing and unknown-cooldown owners remain 503. These responses
do not drop history, migrate signed state, spend reset grants or enable overage.

For example, an owner with five_hour exhaustion until 13:19:59Z returns a message
naming that observed window, resets_at (Unix seconds), resets_in_seconds and a
positive ceil-rounded Retry-After. If weekly exhaustion lasts longer, that later
barrier determines recovery. Unknown applicable deadlines omit timing rather
than promising recovery at another account's reset. Responses WebSocket errors
carry the same detail and a safe retry-after field in their headers object; the
socket itself remains usable. A client may stop rather than wait automatically;
neither retry timing nor 429 guarantees client-driven resumption.

Source inspection on 2026-10-01: OpenCodex
ef0297f86c4540c7d757c8595170d66f9c584aec uses AnthropicAccountCooldownError
with 429 and bridges HTTP retry headers into WebSocket error frames. CLIProxyAPI
fd48ea6840f5572deb53aeb5657740937ac9daaa returns model_cooldown 429 with
reset_seconds/Retry-After. Agent LB
c7f83276e4c8af0d7735adb6524fc68d34a97732 returns 429 with quota recovery
metadata. These support error semantics, not cross-account signed-state
portability. Route mocks verify no dispatch or history mutation; live client
backoff behavior is not independently qualified by these tests.

## Interrupted assistant turn recovery (2026-10-01)

Codex may retry after receiving only an assistant progress message. Anthropic
interprets an assistant-ending Messages request as prefill; Opus 5.5 rejects
that ending. Translated Responses/Chat therefore preserve all projected history
and append a user `(continue)` on the wire. For example, `user: implement` then
`assistant: Writing the proposal` becomes those same messages followed by
`user: (continue)`. Explicit user/tool-result endings need no synthetic turn.
The logical replay store never receives that marker, so empty-delta continuations
do not accumulate artificial user turns. Normal wire caching still applies.

Pending tool calls and search state are validated first. The continuation cannot
supply a missing result or make active signed history portable to another owner.
Native Messages remains caller-owned; compaction already supplies its own user
summary instruction. No client patch, automatic generation replay or history
deletion is involved.

An undeclared tool still fails explicitly. The diagnostic records source/model,
response ID, content index, declaration count and a 12-character SHA-256 name
fingerprint. Only names matching `[A-Za-z0-9_-]{1,128}` are logged in plaintext;
arguments and call IDs are excluded. This makes unexpected tools diagnosable
without guessing aliases or permitting undeclared execution. Structured stream
error delivery is described in `../model-source-routing/spec.md`.

Source evidence inspected October 1, 2026: OpenCodex
`8a005dd98ff12cdc000c6f4961cbf71a592d6b6b`, `src/adapters/anthropic.ts`,
appends `(continue)` for assistant tails. CLIProxyAPI
`d33f63f8e3d98428440ebca5a5b6a981a61ff71e` instead drops unsupported assistant
prefill in its Responses translator; `6f25b9a1` introduced its Opus 5/Sonnet 4.6
rule on August 29. We adopt the history-preserving behavior, not deletion. No
third-party code is copied. Public route/socket mocks verify projection and
recovery, not live upstream OAuth acceptance or the unknown tool's actual origin.

## Portable signed history and unsigned tool turns (2026-10-01)

Compaction previously treated every signed Claude block as a hard account/model
owner and skipped signature recovery. Compacting after a Claude model switch
(Sonnet 5 to Opus 5.5), with the original account paused, or after a historical
signature rejection therefore failed, while a normal turn on the same history
succeeded by omitting that thinking. Omission was rejected for compaction because
it loses content the summary should cover; the only alternative considered was
refusal.

Completed thinking now only prefers its account. Normal turns keep omission:
Anthropic allows omitting prior-turn thinking outside the active tool turn and
filters it per model anyway (Haiku keeps only the last turn). Compaction reads
instead: completed thinking that cannot keep its signature on the selected route
becomes readable assistant text, and redacted thinking is omitted. Compaction's
one-shot signature recovery converts the same way. This is Sub2API's
`FilterThinkingBlocksForRetry` strategy ("preserve content as text", `d6adebd`),
applied deterministically. Converting rather than replaying signatures on another
account also avoids depending on OmniRoute's observation (`dbe703a0`) that
signatures survive an OAuth account switch, since Sonnet 5.5 blocks are
documented as account-bound. The active turn is decided by the same
client-history boundary as foreign reasoning, so the summarizer instruction never
makes completed thinking active. Active signed state and search stay hard owners.
For example, Opus 5 thinking "use the cached index" followed by `/compact` on
Sonnet 5 sends that sentence as an assistant text block.

Manual budget thinking (Haiku 4.5, Sonnet 4.5) requires the final assistant turn
of a thinking-enabled request to begin with a thinking block; adaptive mode drops
that requirement, and one turn runs in a single thinking mode (Anthropic thinking
guide, read 2026-10-01). Claude Code #14264 shows the resulting 400, "Expected
`thinking` or `redacted_thinking`, but found `tool_use`". Sol tool loops with
plaintext reasoning, adaptive Claude turns that skipped thinking, or an effort
change mid-loop reach that state. When the first assistant message after the last
user message without a tool result lacks leading signed thinking, the budget
request sends `thinking: {"type":"disabled"}`, the value Claude Code sends and the
documented thinking-off setting for both models (OpenCodex `ef0297f` live table:
Haiku 4.5 accepts it). A user message that directly follows a tool output is
merged into the tool-result message on the wire and still belongs to the open
turn. Sub2API removes top-level thinking reactively after such 400s; the structure
is known before dispatch, so no rejected request is spent. CLIProxyAPI `fd48ea6`
disables thinking only for forced tool choice, and OpenCodex replays only genuine
signatures without covering this case. Adaptive Opus 5.5 and Fable reject every
off switch, so they are not changed.

Not live-qualified: Anthropic acceptance of converted thinking text after a real
model or account switch, Fable 5.1 prefix binding over projected history, and the
disabled-thinking continuation on a production Haiku/Sonnet 4.5 account.

### Client-scoped history authentication

Conversation IDs come from caller headers (`thread-id`, Claude Code session), so
under one API key they identify routing and retention context, not a principal.
Envelopes and native resource origins therefore authenticate against client scope;
model and account ownership come from the encrypted envelope or recorded origin.
Example: a Codex fork of an Opus thread replays its parent's signed thinking under
the child `thread-id`; completed thinking prefers its original account and active
reasoning or search still requires it. Fork metadata (`forked_from_thread_id`,
`parent_session_id`) is never an authorization input; the latter remains an
affinity hint only. Older envelopes still carry an ignored conversation field.

### Refusal and stop diagnostics

Translated Claude projections report `stop_reason: "refusal"` as incomplete
`content_filter` regardless of reasoning display. Codex turns that into
`ContentFilter`, records its content-filter guidance and retries; a completed
refusal would instead end the task silently. OpenCodex `249462bf5` (#4312) maps
the same way; CLIProxyAPI `2044a01f4` only on Chat. Native Messages clients see
the raw stop reason and are unchanged.

Every translated message stop logs `claude_message_stop` with stop reason,
status, upstream block type counts and output tokens, so reasoning-only or empty
turns (seen 2026-10-03 00:45–01:09 UTC on Opus 5.5) can be classified. An
empty-completion guard is deferred until those logs show the cause; Codex
already retries stream errors itself and persists reasoning items as they finish.
