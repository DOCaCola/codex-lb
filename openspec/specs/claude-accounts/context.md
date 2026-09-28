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
Usage includes uncached input, cache reads and cache creation; cache creation is
included in total input and exposed separately in Responses usage details. Ledger
costs use the existing model-source pricing semantics, not subscription charges;
there is no separately priced cache-write ledger bucket in this change.

Portable text, images and function/free-form custom tool histories are projected.
Tool namespaces use deterministic reversible names. Signed thinking stays in
encrypted account/model/client/conversation-bound envelopes, never fabricated
reasoning summaries. JSON-schema output and adaptive reasoning use explicit model
policies; unknown model minors do not inherit capabilities optimistically. Grammar
constrained tool decoding, files, built-in server tools other than web search, verbosity,
automatic truncation and paid service tiers have explicit unsupported errors.
Native Messages may carry native extensions without pretending they are Responses
features. Switching models with signed state requires portable context.

Responses continuation uses the existing encrypted disk replay store (one-hour
retention). Complete and incomplete Claude output is saved before terminal delivery.
Compaction uses the selected Claude account for summary generation and the existing
encrypted compaction envelope for portable summary restoration. Native Messages
retains only a scope hash/account/expiry in the database, not conversation text;
its sliding ownership TTL is one hour. Missing signed-history owners fail closed.

## Monitoring and UI

Accounts appear in shared dashboard cards/table, account selection, and Add account.
Controls include pause/resume, refresh, reconnect, selected models, context/output
caps and the global advertised-version pin. Privacy blur and read-only permissions
apply. Missing quota windows show unknown; stale data is labeled, not reset to zero.
Enabled accounts trigger leader-owned quota refresh every minute, catalog refresh
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
uses the existing account/model/client/conversation binding and durable replay
store. Missing or altered state, incompatible scope and unavailable owners fail
explicitly; no encrypted result is fabricated from citations. Search errors or
unfinished server calls cannot be reported as successful completion.

Translated requests stamp default five-minute ephemeral cache boundaries on the
last system block (or last tool if there is no system block), plus the last two
cacheable user-turn tails. Native cache markers and signed server blocks remain
untouched. These are eligibility hints, not a guarantee of cache hits.

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

After native account rebinding, resource ownership is ambiguous: server-resource
history fails explicitly rather than being assigned to the new account. This
marker is scoped and expires with session retention; it is not conversation storage.
Translated Responses envelopes and their ownership checks remain unchanged.
Reference evidence: OmniRoute PR #7906, OpenCodex native versus translated replay,
CLIProxyAPI parent affinity. These are source/mock checks, not live OAuth acceptance.
