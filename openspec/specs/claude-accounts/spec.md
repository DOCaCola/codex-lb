# Claude Accounts

## Purpose

Provide separately owned Claude OAuth credentials and faithful native and adapted inference without an intermediate gateway.

## Requirements

### Requirement: Claude Chat routing without upstream Chat capability

An enrolled Claude OAuth source SHALL serve authorized `/v1/chat/completions` requests through its Responses capability without being marked as an upstream Chat Completions source. Existing enabled accounts SHALL be eligible without re-enrollment. Disabled, unauthorized and exhausted Claude pools MUST NOT fall back to OpenAI subscription accounts.

#### Scenario: Existing enrolled account
- **WHEN** an enabled Claude model is requested on the Chat endpoint
- **THEN** the existing Claude account pool handles the request through its normal owner and transport

#### Scenario: Signed Chat tool replay
- **WHEN** a keyed client resends complete Chat tool history matching one live record
- **THEN** Claude receives the original authenticated signed thinking on its original account and model
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

### Requirement: Shared Claude routing policy
Claude SHALL use the dashboard routing strategy, earlier-reset preference and
relative-availability tuning through the shared strategy implementation. Claude
SHALL supply normalized equal account capacities, never OpenAI plan estimates.
Fresh five-hour usage SHALL map to primary; fresh applicable weekly pressure
SHALL map to secondary. Unknown/stale ranking data SHALL follow an explicit
neutral policy, not be represented as observed zero usage.
Authorization, quota exclusion, hard ownership and eligible affinity SHALL remain
enforced. Single-account mode SHALL use a distinct Claude target and fail closed
when missing, unavailable or conflicting with resource ownership. Successful
source admission SHALL update Claude selection recency.

#### Scenario: Earlier-reset policy
- **WHEN** an unbound Claude request uses reset-drain
- **THEN** eligible normalized candidates follow the same reset-drain ordering as Codex

#### Scenario: Provider-specific single account
- **WHEN** single-account mode selects an OpenAI target but no Claude target
- **THEN** Claude fails explicitly without using the OpenAI account or guessing a Claude target

#### Scenario: Bound conversation
- **WHEN** quota ranking favors another account but an eligible hard owner is required
- **THEN** the hard owner remains selected

### Requirement: Native Claude affinity and signature recovery
Native first-party thinking history SHALL remain unchanged in ordinary requests.
Thinking alone MUST NOT require an unexpired account-owner record. Account
preference SHALL be subordinate to authorization and eligibility. Native server
resource state SHALL resolve observed resource origins independently of affinity.
Account rebinding MUST NOT transfer resource ownership or prevent replay of a
known resource on its authorized original account.

#### Scenario: Idle thinking conversation
- **WHEN** a native conversation resumes with thinking after affinity expires
- **THEN** it may select an eligible account without altering its thinking

### Requirement: Bounded historical signature recovery
Messages forwarding SHALL retry at most once on an upstream HTTP 400 explicitly
rejecting a thinking-block signature, before output delivery. Recovery SHALL
change only completed historical thinking, preserve active ordinary and server
tool cycles, and leave all visible content and tool pairs unchanged. Normal
translated and native requests SHALL remove that thinking. Compaction SHALL
convert historical thinking to readable text and remove redacted thinking. If
the change would leave an empty message or no safe change exists, it SHALL
return the error. Generic errors, 429s and latest-assistant-modification errors
MUST NOT trigger it.

#### Scenario: Historical rejection
- **WHEN** an upstream rejects an eligible historical thinking signature
- **THEN** one same-target recovery attempt is allowed, without changing accounts

#### Scenario: Compaction rejection
- **WHEN** an upstream rejects a historical thinking signature in a compaction request
- **THEN** the single recovery attempt carries that thinking as text so the summary keeps its readable content

### Requirement: Scoped parent affinity
Native sessions SHALL use explicit session headers or structured session metadata,
reject conflicting identities, and allow an eligible parent's account preference
only within the same authenticated client and model scope.

#### Scenario: Child session
- **WHEN** a child starts without its own affinity and its parent has an eligible account
- **THEN** it prefers the parent's account without overriding hard resource ownership

### Requirement: Explicit encrypted credential enrollment
Operators SHALL enroll Claude accounts through expiring single-use PKCE authorization or explicit Claude Code credential-file import. Credentials MUST be encrypted at rest, excluded from dashboard output and logs, and never read implicitly from server-local files. Imported expiry MUST be interpreted as milliseconds and validated. Enrollment MUST warn against concurrent refresh consumers.

#### Scenario: Invalid imported expiry
- **WHEN** a credentials file has missing, invalid or second-based expiresAt
- **THEN** enrollment fails explicitly without creating a usable account

#### Scenario: Reconnect to a different account
- **WHEN** replacement credentials authenticate a different account or organization
- **THEN** reconnect fails without replacing credentials or retained ownership

#### Scenario: Refresh races reconnect
- **WHEN** a reconnect replaces credentials while an older refresh attempt remains in flight
- **THEN** the old generation cannot overwrite the replacement credentials

#### Scenario: Duplicate rotated grant
- **WHEN** a different current grant authenticates an already enrolled account and organization
- **THEN** enrollment rejects the duplicate using authenticated identity rather than the access token or display name

### Requirement: Refresh rotation ownership
Refresh MUST use durable cross-worker ownership and generation checks. Explicit invalidation MUST require reauthentication; definitive transient rejections MUST permit a later retry after backoff. Uncertain consumption MUST NOT blindly replay the refresh token, and known expired access tokens MUST NOT be dispatched.

#### Scenario: Ambiguous refresh outcome
- **WHEN** a refresh dispatch times out or the worker dies with a recorded intent
- **THEN** later workers report uncertain credential state instead of rotating the same grant again

### Requirement: Selected catalog and pooled routing
Explicitly selected available models, or all discovered models with resolved capabilities when All models is enabled, on enabled, credential-healthy and client-authorized accounts SHALL be routed. Selected mode SHALL be the default and synchronization MUST preserve curated choices across mode switches. Catalog synchronization MUST paginate atomically and retain the previous snapshot on failure. Quota monitoring SHALL represent observed shared and model-specific windows and unknown/stale state truthfully. Pool attempts MUST preserve model, opaque-state ownership, admission and exactly-once settlement; no retry SHALL occur after visible output or ambiguous dispatch.

#### Scenario: Automatic Claude catalog
- **WHEN** All models is enabled and discovery adds a model with resolved limits
- **THEN** it becomes available while unavailable models remain disabled and curated selections are retained

#### Scenario: Model-specific exhaustion
- **WHEN** an account has an exhausted model-specific window
- **THEN** that account is ineligible for that model without disabling unrelated models

#### Scenario: Unavailable continuation owner
- **WHEN** account-bound continuation names a paused, unauthorized, refreshing or quota-exhausted owner
- **THEN** selection returns an explicit owner-unavailable error without choosing another account

#### Scenario: Worker-independent affinity
- **WHEN** separate workers evaluate an admitted conversation with the same client scope and model and an eligible retained owner
- **THEN** account selection honors its durable affinity regardless of database row order

#### Scenario: Missing quota and entitlement information
- **WHEN** quota monitoring omits a window or returns null
- **THEN** the dashboard represents it as unknown, not zero usage or a denied model entitlement

#### Scenario: Stale exhausted quota
- **WHEN** an exhausted window has a future reset but monitoring has become stale
- **THEN** its known exhaustion continues to block applicable models until reset or a newer observation
- **AND** passing its reset changes the observation to unknown rather than fabricating zero usage

### Requirement: Native billing-first layout preservation
The gateway SHALL recognize a leading Claude Code billing system block as native
payload identity only when the existing CLI software and OAuth header checks
succeed. Recognized native requests MUST preserve system block order and cache
breakpoints without synthesizing, relocating or stabilizing billing content.

#### Scenario: Native billing-first helper
- **WHEN** qualifying Claude CLI headers accompany a billing-first system array
- **THEN** forwarding preserves the system array and cache breakpoints
- **AND** a non-qualifying client does not gain native recognition from text alone

### Requirement: Native Messages fidelity
Authenticated `/v1/messages` and `/v1/messages/count_tokens` SHALL preserve supported recognized native body fields, system block order, cache markers, tool identifiers, beta/version metadata, SSE pings, upstream error status and rate-limit information. Caller credentials and hop-by-hop headers MUST NOT reach upstream. Native recognition MUST NOT grant authentication or change global version state. Third-party Messages SHALL use the same explicit OAuth compatibility policy as translated Responses. Unsupported billing semantics MUST fail explicitly rather than silently change spending policy.

#### Scenario: Native extension fields
- **WHEN** a client sends safeguards and corresponding beta metadata
- **THEN** these reach the trusted Anthropic destination without flattening its system array

#### Scenario: Native stream transport failure
- **WHEN** the upstream Messages stream fails after downstream headers were sent
- **THEN** the gateway settles the failed attempt and returns a native SSE error event, not a Responses envelope or successful message_stop

### Requirement: Codex protocol adaptation
Claude SHALL support Responses over downstream HTTP and WebSocket while using HTTPS/SSE upstream. Translation MUST preserve portable text, tool/custom-tool/namespace, image, reasoning and cache-usage semantics, or reject unsupported semantics explicitly. Truncation and pause_turn MUST NOT become completed. Durable continuation MUST be persisted before terminal delivery and scoped to compatible account/model state; compaction MUST preserve useful context.

#### Scenario: Pause turn
- **WHEN** Anthropic stops with pause_turn
- **THEN** the Responses client receives an incomplete result and no hidden automatic continuation

#### Scenario: Unsupported constrained output
- **WHEN** a Responses request asks for unsupported grammar-constrained tool decoding or a provider-specific control without a Claude equivalent
- **THEN** the adapter returns an explicit unsupported-parameter error before dispatch rather than silently ignoring it

#### Scenario: Native resource history outlives provenance retention
- **WHEN** native resource history is submitted after its thirty-day resource provenance expires
- **THEN** it fails explicitly and requires portable context rather than guessing its origin from affinity

### Requirement: Advertised version following
The service SHALL asynchronously follow the canonical stable Claude Code release at startup when stale and every 24 hours, sharing state across workers. It MUST preserve the last valid version on discovery failure, distinguish last checked from last changed, support manual pin/rollback, and use one immutable identity snapshot per request. It MUST NOT download executable updates or fabricate private billing fingerprints.

#### Scenario: Unchanged version check
- **WHEN** discovery succeeds with the current version
- **THEN** last checked advances while last changed remains unchanged

### Requirement: Unified account controls
Claude SHALL appear alongside existing accounts in account and dashboard collections, with the shared add-account chooser, pause/resume, privacy and read-only controls. Quotas and API-equivalent token costs MUST remain distinguishable from actual subscription charges.

#### Scenario: Paused Claude account
- **WHEN** an operator pauses a Claude account
- **THEN** it stays visible in the shared account list but cannot serve new inference

### Requirement: Qualification boundary
Local tests SHALL cover two-account routing, refresh/restart, native and translated streams, tools, continuation and cancellation. Release documentation MUST distinguish mock/source verification from live OAuth acceptance and billing qualification. Compatibility transformations MUST be applied before dispatch under a versioned policy, not as hidden retries to conceal an eligibility rejection. No paid fallback SHALL conceal an upstream eligibility rejection.

#### Scenario: Upstream eligibility rejection
- **WHEN** upstream rejects the client's eligibility for included usage
- **THEN** the error remains visible without enabling extra usage or rotating through the pool blindly

### Requirement: Versioned OAuth request profile
Third-party OAuth traffic SHALL use one immutable profile snapshot for each outbound attempt. Management, Messages and count-tokens SHALL have distinct header policies. Session identity MUST be bound to account and client conversation and remain stable across token rotation. Instruction relocation MUST preserve block contents and cache markers, use explicit model capabilities, preserve tool-use/result adjacency and leave signed turns unchanged. Broad text obfuscation and silent instruction deletion MUST NOT occur. Logical history MUST remain separate from projected wire history.

#### Scenario: Legacy model instruction placement
- **WHEN** translated instructions target a supported legacy model without mid-conversation system support
- **THEN** original instruction blocks are preserved in an explicit user reminder and the role-authority change is recorded by the selected profile

#### Scenario: Updated native client
- **WHEN** recognized Claude Code supplies a newer patch in the supported major/minor series
- **THEN** its native profile is preserved without changing the server's discovered or pinned version

### Requirement: Coherent Claude wire policy
Outbound Claude session headers and structured body session metadata MUST use the
same account/client/conversation-bound identity, stable across token refresh.
Projection MUST NOT mutate logical history or unrelated metadata. Malformed or
unsupported session metadata MUST fail before credential refresh or dispatch.
Native negotiated beta tokens and reviewed helper, agent and compaction hints
SHALL survive forwarding without unsolicited thinking, effort or tool activation.
Native request IDs and retry counts SHALL be preserved independently of gateway
attempt IDs. Native helper/count-token recognition MUST NOT require the main
agent system identity when their supported endpoint/profile signals are present.
Synthesized Messages SHALL advertise a timeout; count_tokens SHALL not synthesize
that field. Transport MUST own compression negotiation.

#### Scenario: Native session metadata
- **WHEN** a native request carries structured session and parent-session metadata
- **THEN** both are scoped consistently with the upstream session header without changing logical history

#### Scenario: Native feature negotiation
- **WHEN** native thinking or output configuration is forwarded
- **THEN** the gateway preserves negotiated betas without inferring extra thinking or tool features

#### Scenario: Helper request
- **WHEN** a recognized native helper lacks the main CLI system identity
- **THEN** its supported body and caller hints are preserved instead of relocated

#### Scenario: Unsupported metadata
- **WHEN** session metadata cannot be safely projected
- **THEN** preparation fails explicitly before token refresh or upstream dispatch

### Requirement: Translated hosted web search
Translated Claude Responses SHALL accept nameless web_search declarations and map supported live search options to native Anthropic search. A declaration with external_web_access=false SHALL be omitted, allowing conversation to continue without granting cached or live search through that tool. Other unsupported options MUST fail before dispatch rather than silently weaken caller constraints. HTTP and WebSocket Responses SHALL expose search lifecycle and URL citations, preserve real upstream search state across continuation, and reject missing, tampered or cross-account/model/client/conversation replay state. Server search errors and unfinished searches MUST NOT become successful completion.

#### Scenario: Default Codex search declaration
- **WHEN** Codex includes a nameless live web_search tool
- **THEN** the request reaches Claude as a versioned server-search declaration instead of failing name validation

#### Scenario: Cached-only search
- **WHEN** Codex includes web_search with external_web_access=false
- **THEN** the declaration is omitted and the remaining conversation and tools proceed without enabling live search

#### Scenario: Search continuation
- **WHEN** a client replays search output with its authenticated opaque state
- **THEN** the exact upstream search blocks are restored under the same authorized owner

#### Scenario: Missing search state
- **WHEN** a search output has no matching authenticated opaque state
- **THEN** preparation fails explicitly without dispatch

### Requirement: Translated cache boundaries
Translated Responses SHALL produce deterministic ephemeral cache boundaries for stable instruction/tool prefixes and recent user history, within Anthropic's four-breakpoint limit. Proxy-generated boundaries SHALL use the default 5m tier. Native caller markers and signed server content MUST remain unchanged. Projection MUST NOT mutate retained logical history.

#### Scenario: Subsequent translated turn
- **WHEN** a translated conversation adds another user turn
- **THEN** stable prefix and recent user-turn cache boundaries are present without changing prior text or signed blocks

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against client and conversation before routing. Completed thinking SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking from outbound projection while preserving visible text and paired tools and leaving retained history unchanged; compaction SHALL instead project completed thinking as readable historical assistant text and omit only redacted thinking. It SHALL record conversion and omission counts without content or credentials. Active reasoning and server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking completed; compaction SHALL determine this on the client-supplied history excluding its summarization instruction. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Compaction on another route
- **WHEN** compaction selects another account or model than completed thinking
- **THEN** the summarizer receives that thinking as readable assistant text in its original position, without a signature

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active reasoning

#### Scenario: Authenticated Chat tool cycle
- **WHEN** a keyed Chat client resends the complete visible history and all tool results for one live Claude tool response
- **THEN** the gateway restores only that response's genuine signed or redacted thinking under the same conversation, model and account owner
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client or conversation
- **THEN** preparation fails before upstream dispatch

### Requirement: Synthesized identity coherence
Translated Messages SHALL include a stable local device identity and the same scoped session identity in body metadata and headers. Unknown provider account identity MUST NOT be fabricated. Synthesized OS and architecture SHALL match the runtime; native reviewed headers SHALL remain caller-owned. No billing fingerprint SHALL be synthesized.

#### Scenario: Rotated credentials
- **WHEN** the selected account refreshes its token within the same client conversation
- **THEN** local device and session metadata remain stable without reusing identity across another client or account

### Requirement: Reactive Claude quota failover
The gateway SHALL classify upstream 429 refusals before health mutation. Fast-mode credit entitlement refusals SHALL NOT cool the pool. Shared or ambiguous unified quota rejection SHALL cool the account; proven overage-only and ordinary model limits SHALL cool only the requested model. Each restriction SHALL use only its attributable deadlines: a valid Retry-After SHALL be a minimum wait alongside explicit rejected-window resets, then an attributable aggregate reset when window resets are unavailable, then a 60-second default. Deadlines SHALL persist and never shorten on concurrent writes. The gateway MAY select another authorized eligible account before output, excluding failed accounts, and MUST rebuild identity, credentials and history projection for that target. Active reasoning and server-resource ownership MUST remain enforced. A logical request SHALL permit at most four physical sends including signature recovery. Canceled requests and errors after stream ownership SHALL NOT trigger account failover. Every failed attempt SHALL settle and release admission before another attempt; exhausted recovery SHALL preserve the last upstream refusal.

#### Scenario: Alternate succeeds
- **WHEN** account A returns a retryable 429 and account B is eligible
- **THEN** B receives a freshly prepared request after A settles

#### Scenario: Entitlement refusal
- **WHEN** upstream refuses fast mode for missing credits
- **THEN** the refusal is returned without cooling ordinary account traffic

#### Scenario: Bounded recovery
- **WHEN** all selected accounts refuse or signature recovery consumes the send budget
- **THEN** no more than four physical sends occur

#### Scenario: Owned history
- **WHEN** active reasoning or server resources prevent account migration
- **THEN** the original refusal is returned without sending to another owner

### Requirement: Generation-aware Claude authentication recovery
Prepared attempts SHALL capture the generation with the credentials actually used. After an explicit pre-output upstream401 authentication failure, the gateway MAY recover once per account per logical request: reuse an advanced generation or force an unchanged ready generation through its durable refresh claim despite future expiry. Successful refresh SHALL persist before replay. Active or uncertain refresh intents MUST NOT be stolen. Cancellation or ambiguous refresh outcome MUST NOT cause a second token exchange. Permission403 and request-specific errors MUST NOT trigger authentication refresh. Repeated401 SHALL impose ten-minute authentication backoff only on the same ready generation without an active intent; it MUST NOT revoke a newer grant. Inference retries SHALL share the four-send budget and settle before retry. Account reselection SHALL preserve authorization and strict history ownership. Failed recovery SHALL retain the upstream authentication refusal when no eligible retry succeeds.

#### Scenario: Future expiry rejected
- **WHEN** an unexpired access token receives upstream401
- **THEN** one claimed refresh and freshly prepared same-account replay are permitted

#### Scenario: Concurrent rotation
- **WHEN** the rejected generation has already been replaced
- **THEN** recovery reuses the newer credential without another token exchange

#### Scenario: Repeated rejection
- **WHEN** the recovered account receives another401
- **THEN** the rejected generation receives bounded auth backoff and no second auth recovery in this request

#### Scenario: Uncertain exchange
- **WHEN** refresh may have consumed the rotating grant
- **THEN** the durable uncertain or active intent remains protected from replay

### Requirement: Bounded Claude overload recovery
Explicit upstream 529 or 503 overloaded_error MAY be retried once on the same account before generation. The retry SHALL consume the shared four-send budget and fit a ten-second recovery window from dispatch entry. Valid Retry-After SHALL be a minimum wait; absent hints SHALL use 250–500ms jitter. Waiting SHALL be cancellable and own no admission or reservation. Repreparation SHALL enforce current authorization and history ownership. Overload MUST NOT trigger credential refresh, account rotation or account/provider health penalties.

The gateway SHALL inspect SSE startup within 32 events, 64KiB and its first-frame deadline. Only comments/pings and empty message_start metadata without positive output usage MAY precede a recoverable overloaded_error. Such error SHALL surface as 529 before any public stream event. Content blocks, other generation events or positive output usage SHALL prohibit overload replay. Prelude-limit violations, generic 503, connection failures and timeouts MUST NOT acquire overload retries. Exhaustion SHALL preserve the refusal and retry hint; partial generation SHALL retain normal failure/usage handling.

#### Scenario: Early SSE refusal
- **WHEN** HTTP 200 contains pings followed by overloaded_error before generation
- **THEN** the failed attempt closes and may retry on the same account without publishing its events

#### Scenario: Output already started
- **WHEN** overload follows a content block or positive output usage
- **THEN** the gateway does not replay the generation

#### Scenario: Wait exceeds recovery window
- **WHEN** Retry-After cannot fit the remaining recovery window
- **THEN** the original refusal is returned without shortening its requested wait

### Requirement: Capacity-aware Claude admission
Claude account settings SHALL expose a nullable positive-integer max_concurrency, default unlimited, enforced per worker using the existing source bulkhead. Atomic admission SHALL precede API-key reservation and inference sends. When a candidate is full, portable requests SHALL try other authorized eligible accounts, visiting each rejected candidate at most once. Hard history owners and same-account auth/overload retries MUST NOT move due to capacity. Selection exhaustion SHALL return 503 model_source_busy with Retry-After: 1. Local saturation MUST NOT consume physical-send budget, refresh credentials as error recovery, record quota cooldowns, or penalize account health. Every acquired claim SHALL retain exactly one cleanup owner and be released on cancellation, failure or completion.

Native affinity SHALL be persisted only after successful admission. Concurrent incompatible ownership changes SHALL fail before inference with a retryable claude_session_changed error, releasing admission.

#### Scenario: Soft preference is full
- **WHEN** a portable request prefers a full account and another eligible account has capacity
- **THEN** it is reprepared and sent using the available account

#### Scenario: Hard owner is full
- **WHEN** an account-bound request's owner is full
- **THEN** the gateway returns local busy without sending through another account

#### Scenario: Clearing the limit
- **WHEN** an operator clears the concurrency setting
- **THEN** the saved value is null and dispatch is unlimited

### Requirement: Live Claude quota observation
The gateway SHALL observe valid five-hour and seven-day utilization headers on physical Claude HTTP responses, including rejected attempts, before retry or stream completion. Observations SHALL be attributed to the sending source and credential generation; stale-generation or deleted-account observations MUST NOT persist. Finite nonnegative header fractions SHALL become percentages, including values above 100%; malformed, negative or nonfinite converted values SHALL leave prior evidence unchanged. The gateway MUST NOT guess alternative scales or clamp stored utilization. Missing/reset-only headers MUST NOT invent usage or extend retained usage.

Window freshness and provenance SHALL distinguish header receipt from polling. Header updates MUST NOT mark unrelated windows fresh, clear poll errors, erase model-specific windows or clear refusal cooldowns. Request-start ordering SHALL prevent older concurrent requests from replacing newer observations; expired evidence SHALL be unknown. Atomic bounded merges SHALL preserve concurrent settings/catalog updates. History sampling SHALL be bounded to one header sample per account/window/minute. Observation failures MUST NOT fail or retry inference; cancellation and upstream ownership SHALL remain intact.

#### Scenario: Failover attribution
- **WHEN** account A returns quota headers with 429 before account B succeeds
- **THEN** both observations belong to their respective sending accounts

#### Scenario: Partial observation
- **WHEN** headers contain only five-hour utilization
- **THEN** other windows retain their previous evidence and freshness

#### Scenario: Replaced credentials
- **WHEN** a physical response arrives after its sending credential generation was replaced
- **THEN** its quota observation is discarded

#### Scenario: Utilization overshoot
- **WHEN** a fresh five-hour utilization header contains 1.04
- **THEN** persisted usage and dashboard text report 104%, the window is exhausted, and remaining-quota bar width is zero

### Requirement: Scoped Claude overage restrictions
Claude 429 recovery SHALL distinguish shared subscription rejection from requested-model overage or entitlement rejection. Healthy shared windows with explicit overage-only evidence SHALL NOT create an account-wide restriction. An omitted shared-window status SHALL require finite nonnegative utilization below one and another explicitly allowed shared window to establish health; missing or malformed usage MUST NOT imply health. Explicit shared rejection SHALL retain account-wide scope. Structured credits_required errors SHALL restrict the requested model without suppressing independently rejected shared windows. Fast-mode entitlement refusals SHALL retain existing no-failover behavior.

Mixed shared and model rejection SHALL preserve both restrictions atomically with independently attributable deadlines. Model-specific Retry-After or reset MUST NOT extend shared cooldowns. Aggregate deadlines SHALL apply only to an identified scope or the sole unambiguous scope; otherwise the existing default SHALL apply. Existing longer restrictions MUST NOT be shortened or cleared. Restrictions MUST NOT infer additional affected models from a model-family name. Authorization, hard ownership, settlement ordering and physical-send budgets SHALL remain unchanged across native Messages, count_tokens and Responses HTTP/WebSocket paths.

#### Scenario: Overage-only refusal
- **WHEN** a model is rejected for overage while shared subscription windows are healthy
- **THEN** that model is restricted but sibling models remain selectable on the same account

#### Scenario: Model-window overshoot
- **WHEN** a 429 reports finite model-window utilization at or above one while shared windows are healthy
- **THEN** the requested model is restricted using its window deadline even if its status header is absent

#### Scenario: Mixed rejection
- **WHEN** a shared window resets in two hours and a model window resets in eighty hours
- **THEN** both restrictions persist and after two hours only the affected model remains restricted

#### Scenario: Ambiguous unified rejection
- **WHEN** unified status is rejected without enough evidence to isolate an overage-only failure
- **THEN** account-wide protection is retained and missing usage is not interpreted as healthy

### Requirement: Manual Claude reset grants
The dashboard SHALL discover cedar_ember grants for a specific authenticated Claude account and distinguish unavailable or malformed data from zero grants. Redemption SHALL require dashboard write authorization, explicit confirmation, a selected grant and operation UUID. New spends SHALL verify fresh eligibility, usability, remaining count, validity period and at-limit requirements. The organization SHALL derive from the credential's verified identity. No automatic spending or account failover SHALL occur.

Operation intent SHALL persist before POST. Concurrent attempts SHALL be serialized without holding database locks during network I/O. Identity mismatches SHALL be refused. Terminal results SHALL replay without another POST; unknown outcomes SHALL retain the operation ID and remain visible after reload/restart. Explicit same-ID retries SHALL be bounded to ten minutes from intent and respect an execution lease. New operations after expired uncertainty SHALL require a separate explicit risk acknowledgement and fresh grant eligibility. Cancellation, timeout, malformed answers and settlement-write failure MUST NOT be reported as proof that nothing was spent.

Confirmed reset results and cleared windows SHALL persist atomically with local reconciliation. Only attributable pre-reset quota restrictions for returned cleared windows SHALL be invalidated. Unknown legacy restrictions, entitlements, auth failures, uncleared windows and newer observations SHALL survive. Late pre-reset observations MUST NOT restore cleared evidence. Cleared quota SHALL become unknown until refreshed rather than fabricated zero. A refresh failure after confirmed redemption SHALL remain distinct from a failed redemption.

#### Scenario: Confirmed manual reset
- **WHEN** an authorized operator confirms a usable grant
- **THEN** one durable operation owns the claim and the dashboard shows the settled result and refreshed quota status

#### Scenario: Unknown claim outcome
- **WHEN** the claim times out after intent is persisted
- **THEN** the dashboard retains an uncertain operation and offers only bounded same-ID retry until the retry window expires

#### Scenario: Selective reset
- **WHEN** a reset clears five_hour but not seven_day
- **THEN** older five-hour evidence is invalidated while weekly, unrelated and newer restrictions remain effective

### Requirement: Claude pool exhaustion diagnostics
Selection SHALL distinguish quota-only exhaustion from other unavailability within the authorized model/owner scope. Quota-only exhaustion SHALL return429, including a required continuation owner; mixed or unknown unavailability SHALL retain503. Known candidate recovery SHALL account for every applicable temporary barrier, using the latest deadline per candidate and earliest across fully known candidates. Unknown deadlines MUST NOT be fabricated. Hard owner errors SHALL retain their code and scope. Quota refusals SHALL identify observed blocking windows without exposing account identities or history. HTTP errors SHALL include a ceil-rounded positive Retry-After when justified. Known recovery SHALL include resets_at and resets_in_seconds in public error details; downstream Responses WebSocket errors SHALL preserve those details, status and safe Retry-After. Actual exhausted upstream errors and local admission contracts SHALL remain unchanged.

#### Scenario: Multiple restrictions
- **WHEN** one candidate has quota reset in two hours and model cooldown in five, and another recovers in three
- **THEN** the reported known recovery delay is three hours

#### Scenario: Known exhaustion without a deadline
- **WHEN** all candidates are quota-exhausted but no candidate has a complete recovery deadline
- **THEN** the response remains429 without a fabricated Retry-After or reset fields

#### Scenario: Quota-blocked continuation owner
- **WHEN** active signed history or server resources require a quota-exhausted account and another account is eligible
- **THEN** the gateway returns429 rate_limit_error with previous_response_owner_unavailable, observed blocking windows and only the owner's known recovery timing
- **AND** no alternate account is dispatched and retained history remains unchanged

#### Scenario: Non-quota continuation owner
- **WHEN** the required owner is paused, unauthorized, refreshing or blocked by unknown cooldown evidence
- **THEN** the owner error remains503 without becoming a quota-only refusal

#### Scenario: WebSocket quota refusal
- **WHEN** a downstream Responses WebSocket turn has a quota-only owner exclusion
- **THEN** its error frame carries status429, rate_limit_error, the owner code and available reset fields and retry-after header without leaking credentials

### Requirement: Native resource provenance
Native server-tool history SHALL resolve its authorized source from observed
resource origins, independently of soft session affinity. Origins SHALL be
scoped to client, conversation and model, retained for thirty days of authorized
use, and persisted before output exposing the identifier. Unknown, expired or
conflicting origins SHALL fail explicitly without inferring ownership from
affinity or incoming history. Ordinary tools and translated replay SHALL retain
their existing contracts. Count-token requests SHALL NOT create or extend origins.
Unsupported native file/container resource references SHALL fail explicitly.

#### Scenario: Affinity expires
- **WHEN** native history replays a retained resource after affinity expires
- **THEN** the request selects the resource's authorized origin account

#### Scenario: Branch rebinds
- **WHEN** different branches obtain resources on different accounts
- **THEN** each resource resolves independently and mixed-origin history fails

#### Scenario: Persistence fails
- **WHEN** a new resource origin cannot be committed
- **THEN** its identifying output is not delivered and generation is not retried

### Requirement: Optional model-specific quota presentation
Claude quota responses SHALL omit null Opus/Sonnet weekly windows when a successful retained usage snapshot establishes they were not reported. Shared windows SHALL retain unknown states when unavailable. Before any successful usage snapshot, scoped windows MAY remain unknown. Known scoped observations SHALL remain visible under stale, expired or reset-barrier states. Missing scoped windows MUST NOT imply model unavailability, unlimited entitlement or shared-quota duplication.

#### Scenario: Pro account without scoped windows
- **WHEN** a successful usage response includes shared windows and null model-specific windows
- **THEN** account details show the shared limits without unknown Opus/Sonnet quota rows

#### Scenario: Previously reported scoped quota is stale
- **WHEN** a scoped observation exists but a subsequent refresh fails
- **THEN** that observation remains visible as stale rather than disappearing

### Requirement: Automatic Claude token capabilities
Claude model selections SHALL contain model identifiers only. Token limits SHALL derive from authenticated discovery with explicitly maintained model metadata for absent fields. Discovery SHALL take precedence. Unknown models missing either limit SHALL remain unavailable with a diagnostic. The dashboard SHALL display resolved provider capabilities without token editors. Existing selected IDs SHALL survive upgrade, but old manual limits MUST NOT remain active. Native explicit output budgets SHALL be accepted within the effective model ceiling; omitted translated budgets SHALL use the lesser of 64000 and the resolved model maximum. Client catalogs SHALL advertise a default Claude context of the lesser of 272000 and discovered capacity, retaining actual capacity separately as max_context_window, with 95% effective context and a separate 90% default auto-compaction threshold. This policy SHALL apply to existing projections at catalog construction without altering persisted capabilities. Existing explicit context overrides SHALL retain their shared override behavior.

#### Scenario: Discovered limits
- **WHEN** discovery reports 1000000 input and 128000 output tokens
- **THEN** provider capability remains 1000000/128000 while clients receive 272000 default context, 1000000 maximum context, 244800 default compaction and 95% effective context

#### Scenario: Smaller model capacity
- **WHEN** discovery reports 200000 input tokens
- **THEN** the default and maximum context remain 200000 with 180000 default compaction

#### Scenario: Existing account projection
- **WHEN** an existing projection contains a 1M capacity and old 900000 compaction hint
- **THEN** catalog construction advertises the current conservative default without rewriting its provider capability

#### Scenario: Unknown limits
- **WHEN** a model lacks discovered and maintained limits
- **THEN** it cannot be newly enabled and no guessed limit is advertised

#### Scenario: Obsolete override
- **WHEN** a model-selection update contains a manual token limit
- **THEN** it is rejected rather than silently stored or ignored

### Requirement: Claude account presentation parity
Claude dashboard cards, account list rows and account details SHALL share the corresponding Codex quota and routing presentation components, percentage/date conventions and information hierarchy. Missing observations SHALL remain unknown, stale observations SHALL be marked, and overshoot SHALL remain observable. Claude-specific credentials, model selections and reset grants SHALL remain accessible. Unsupported OpenAI-specific information MUST NOT be fabricated. Read-only users MUST NOT mutate settings.

#### Scenario: Stale quota
- **WHEN** a Claude account has a stale weekly observation
- **THEN** its shared remaining-quota presentation includes a stale diagnostic instead of claiming fresh data

### Requirement: Claude account routing preference
Each Claude account SHALL support normal, burn_first and preserve routing policies, defaulting to normal. Authorized changes SHALL persist and appear in account views. Claude SHALL pass the policy to the shared scheduler and retain its strategy-specific semantics, authorization, hard ownership and eligible affinity; OpenAI pools MUST NOT be affected.

#### Scenario: Burn preference
- **WHEN** unbound round-robin selection has eligible normal and burn_first Claude accounts
- **THEN** the burn_first account is selected

#### Scenario: Hard owner
- **WHEN** an eligible hard owner has preserve policy and another account has burn_first
- **THEN** the owner is retained

### Requirement: Coordinated Claude metadata refresh
Usage and catalog refreshes SHALL coordinate independently through durable per-account endpoint claims and cooldowns. Scheduled usage refresh SHALL run no more often than every three minutes and catalog refresh every six hours. Manual refresh MAY bypass successful-cache cadence but MUST NOT bypass an active claim or failed-attempt cooldown. Claims SHALL expire after bounded execution and completion SHALL require the owning claim and credential generation. Network I/O MUST NOT hold database write locks.

Last successful observations and timestamps SHALL survive failures. HTTP errors SHALL identify the metadata endpoint without exposing response bodies or credentials. Valid Retry-After seconds or HTTP dates SHALL establish the next attempt time; absent or invalid hints SHALL use three minutes. Failure on one endpoint MUST NOT prevent refreshing the other. Metadata failures MUST NOT pause accounts, penalize inference health, or trigger reactive credential rotation. Fresh inference quota headers SHALL retain their independent authority.

#### Scenario: Rate-limited usage
- **WHEN** usage returns 429 with Retry-After
- **THEN** manual and scheduled refreshes return retained state until that deadline without another usage request, including after worker restart

#### Scenario: Concurrent refresh
- **WHEN** two workers refresh the same endpoint
- **THEN** only the durable claim owner sends and a late or replaced-generation completion cannot overwrite state

#### Scenario: Endpoint isolation
- **WHEN** catalog is cooling down but usage is due
- **THEN** usage still refreshes and catalog retains its last successful data

### Requirement: Claude request usage and timing
Claude native and adapted request logs SHALL preserve inclusive input/output tokens, separately reported cache reads and writes, and only provider-reported reasoning tokens. The gateway SHALL measure upstream-attempt duration and time to first nonempty generated text, thinking or tool payload from a monotonic pre-open anchor. Nonempty redacted-thinking data and thinking signatures SHALL establish opaque first output. Metadata, pings and empty deltas MUST NOT establish first-token latency. Error, cancellation and truncated streams SHALL finalize duration without inventing first-token latency. Timing observation MUST precede Responses adaptation and MUST NOT expose opaque contents or infer reasoning token counts.

#### Scenario: Cached thinking stream
- **WHEN** a stream reports uncached input, cache reads, cache writes and output but no reasoning token count
- **THEN** its inclusive totals and cache breakdown persist, while reasoning tokens remain unknown

#### Scenario: Opaque first output
- **WHEN** a native stream emits nonempty redacted-thinking data or a thinking signature before visible output
- **THEN** TTFT anchors to that opaque upstream output and completion retains the same monotonic attempt anchor
- **AND** empty opaque fields, pings and terminal events alone do not establish TTFT

### Requirement: Estimated Claude throughput validity
Claude TPS SHALL use total reported output tokens over the gateway-observed post-TTFT window and be identified as estimated. A sample MUST have successful status, positive reported output, nonnegative known TTFT and a window of at least one second. Dashboard, Reports and conversation analytics SHALL apply identical validity and numerator rules to existing and new logs without changing stored timings, usage or costs.

#### Scenario: Burst-delivered output
- **WHEN** a successful Claude log reports 578 output tokens, 6713 ms elapsed and 6690 ms TTFT
- **THEN** the request displays no TPS and is excluded from aggregate TPS samples
- **AND** TTFT, duration, usage and costs remain available

#### Scenario: Boundary and reasoning
- **WHEN** a successful Claude log reports 100 output tokens, 1000 ms after first output and a known or unknown reasoning count
- **THEN** estimated TPS is 100 and the aggregate includes one sample without subtracting reasoning

#### Scenario: Unsuccessful or unobserved output
- **WHEN** Claude output is unsuccessful, has no observed first output, has negative TTFT or lacks positive reported output
- **THEN** TPS is unavailable without substituting total duration or a guessed token count

### Requirement: Claude reasoning policies
Known budget-thinking models SHALL advertise reasoning separately from adaptive-thinking models. Requested efforts SHALL map to a documented budget below the effective output cap, and impossible explicit caps SHALL fail before upstream dispatch. Omitted/off reasoning SHALL not enable thinking. Request logs SHALL distinguish requested effort from the actual upstream thinking mode and budget when applicable.

#### Scenario: Haiku reasoning cap
- **WHEN** Haiku 4.5 receives high reasoning with an explicit output cap below the mapped budget
- **THEN** the request fails before dispatch rather than enlarging the cap

### Requirement: Budget thinking in an unsigned open tool turn
Translated Messages requests for budget-thinking models SHALL send `thinking: {"type":"disabled"}` when the first assistant message of the open turn, which follows the last user message without a tool result, does not begin with thinking or redacted thinking. Requested effort SHALL still be validated. The decision SHALL log a content-free diagnostic. Adaptive-thinking models, user-started turns and signed open turns SHALL keep the requested thinking configuration. Native Messages MUST remain caller-owned.

#### Scenario: Foreign tool loop on Haiku
- **WHEN** Haiku 4.5 with reasoning continues tool calls whose assistant turn has no signed Claude thinking
- **THEN** that request disables thinking instead of sending a budget the upstream rejects

#### Scenario: Signed tool loop
- **WHEN** the open turn's first assistant message begins with genuine signed thinking
- **THEN** the budget thinking configuration is sent unchanged

#### Scenario: New user turn
- **WHEN** the request ends with a user message without tool results, including a wire-only continuation
- **THEN** budget thinking is enabled as requested

#### Scenario: Adaptive model
- **WHEN** an adaptive-thinking model continues an unsigned tool loop
- **THEN** the adaptive configuration is sent unchanged

### Requirement: Faithful translated Claude tool schemas
Translated function tools SHALL expose an object input_schema without root oneOf, anyOf or allOf. Ordinary object schemas and nested composition SHALL retain their constraints. Root compositions SHALL use a reversible upstream-only arguments object envelope rather than lossy property merging. Local JSON-pointer references SHALL remain bound to the original schema after relocation. Schemas requiring relocation with unsupported reference scopes, malformed structure or exhausted adaptation budgets SHALL fail before dispatch with the caller-visible tool identity and tools parameter path, without omitting tools or replacing their schema with an unconstrained object.

Completed function arguments SHALL be unwrapped before public Responses output, including HTTP and WebSocket projection. Wrapped argument deltas SHALL remain private until a complete valid envelope is available, then emit original-shape arguments before done. Malformed or oversized envelopes and incomplete JSON MUST NOT be reported as successful tool calls. History SHALL be projected using the current tool declaration's codec; logical replay SHALL retain original client arguments. Tool identity, namespace, choice, call IDs and result pairing SHALL remain stable. Native Messages forwarding SHALL remain outside this translated-schema change.

#### Scenario: Mode-specific tool
- **WHEN** a namespaced function uses root oneOf with different required fields per mode
- **THEN** Claude receives both complete alternatives beneath arguments and Codex receives the unwrapped selected mode

#### Scenario: Fragmented arguments
- **WHEN** a wrapped tool input arrives in partial JSON chunks
- **THEN** no wrapper bytes reach public argument deltas and delta/done/final output agree

#### Scenario: Follow-up history
- **WHEN** the client returns a tool result with its original-shape call history
- **THEN** the adapter encodes that call once according to the current declaration without changing the client history

#### Scenario: Local references
- **WHEN** the original schema references a local definition or its root
- **THEN** relocated references target that original subschema, not the new envelope

#### Scenario: Unsupported reference scope
- **WHEN** adaptation encounters an external reference or a nested schema identifier that cannot safely be relocated
- **THEN** it fails locally naming the tool rather than weakening the contract

### Requirement: Portable standalone tool-output context
Translated Claude Responses over HTTP and WebSocket SHALL preserve a function/custom-tool output with a nonempty call identifier and no corresponding call anywhere in the expanded input as explicitly labeled user context, including supported text and images. The label SHALL identify the original output kind and call identifier. Projection MUST NOT invent a tool call, tool result or signed reasoning, and MUST NOT mutate retained logical history. Real tool results SHALL remain paired exactly once with preceding pending calls. Malformed identifiers, duplicate paired results, outputs preceding their calls and interrupted or incomplete tool cycles MUST fail before dispatch. Standalone context MUST NOT discharge an active pending call. Rejection diagnostics SHALL include the request identifier, item index, output kind, classification, a bounded call-identifier fingerprint and pending-call count, without content or credentials. Native Messages and authenticated continuation/ownership rules SHALL remain unchanged.

#### Scenario: Delegation context without a call
- **WHEN** a Codex request begins with standalone tool output followed by a user instruction
- **THEN** Claude receives labeled user context containing the output and instruction, not an orphan tool_result

#### Scenario: Valid tool continuation
- **WHEN** a retained previous response contains the call corresponding to the submitted output
- **THEN** continuation expansion restores the pair and Claude receives a real tool_use/tool_result cycle

#### Scenario: Duplicate or out-of-order output
- **WHEN** an output repeats a consumed result or precedes its corresponding call
- **THEN** the request fails before upstream dispatch with content-free classification diagnostics

#### Scenario: Incomplete active cycle
- **WHEN** standalone output arrives while a different call remains pending
- **THEN** the request fails without inventing a result or treating standalone context as completion of that call

### Requirement: Canonical Codex external task input
Translated Claude Responses over HTTP and WebSocket SHALL recognize a function_call_output as external task input only when its call_id is omitted, null or a blank string, its id/name/namespace are nonblank strings, and its output is nonblank text or a nonempty array containing only supported text/image blocks with nonblank text or an image. Image blocks SHALL have a nonblank image_url and, if supplied, a valid detail value (auto/low/high/original); the existing Claude image transport/media validation SHALL also apply. Wrong-typed call identifiers, incomplete metadata, blank content and unsupported blocks MUST NOT qualify. The complete output SHALL be preserved in order as ordinary user content without an orphan label, fabricated tool call or signed state. Logical history SHALL remain unchanged. External task input MUST NOT interrupt or satisfy pending tool calls.

#### Scenario: Task input within established history
- **WHEN** a complete external task envelope with null call_id follows completed assistant history
- **THEN** its entire text/image output is projected as new user input and retained logical history keeps the original envelope

#### Scenario: Malformed output cannot masquerade as task input
- **WHEN** an ID-less output lacks required metadata, contains unsupported content, or has a wrong-typed call identifier
- **THEN** it fails explicitly before upstream dispatch without discarding content or inventing pairing

#### Scenario: A task does not complete an active tool call
- **WHEN** canonical external task input arrives before pending tool calls receive their results
- **THEN** the request fails without discharging those calls

### Requirement: External task replay boundary
Canonical external task input SHALL count as a new user turn when classifying completed versus active signed thinking, using the same classifier as protocol projection. All opaque blocks MUST be authenticated before omission. Tool results and malformed task envelopes MUST NOT close active thinking. Server search/resource state SHALL retain its existing strict account/model ownership. Rejected tool-output diagnostics SHALL include identifier presence/type and metadata completeness without raw metadata or content.

#### Scenario: Completed thinking before a new task
- **WHEN** authenticated thinking precedes canonical external task input and the target account/model changes
- **THEN** only completed thinking may be omitted under the existing replay policy, and task content remains intact

#### Scenario: Search ownership is not relaxed by a task
- **WHEN** canonical external task input follows account-bound search history
- **THEN** its search state still requires the original owner and model

### Requirement: Claude history at native Codex dispatch

Native Codex dispatch SHALL authenticate replayed Claude envelopes against the originating client and conversation before projecting history. Readable Claude thinking SHALL become portable reasoning summary text without forwarding Claude encryption, signatures or foreign lookup identities. Existing summaries and distinct plaintext reasoning SHALL be preserved. Projection SHALL leave retained logical history, messages, tool call identifiers and paired outputs unchanged. The same policy SHALL apply to HTTP, WebSocket, retained continuation and native compaction.

Native sanitation SHALL remove invalid known item-type ID prefixes without fabricating identities, preserve valid native opaque reasoning and reject unprojected Claude envelopes. Redacted thinking and Claude-hosted search/resource state SHALL fail before dispatch with `nonportable_provider_history` and an input path instead of being silently deleted or treated as native state. Authentication failures MUST NOT dispatch or penalize an upstream account.

#### Scenario: Opus-to-Sol switch
- **WHEN** a scoped Claude thinking envelope with empty summary and a resp_msg-prefixed reasoning ID is replayed to native Sol
- **THEN** its readable text becomes summary_text and neither its Claude envelope nor foreign ID reaches OpenAI
- **AND** the original retained item remains unchanged

#### Scenario: Tool continuation
- **WHEN** readable Claude thinking accompanies a complete function/custom-tool call and result pair
- **THEN** native projection preserves their identifiers, arguments and outputs in order

#### Scenario: Tampered or cross-scope envelope
- **WHEN** Claude state is invalid or belongs to another client or conversation
- **THEN** the native request fails before upstream dispatch without exposing state contents

#### Scenario: Unrepresentable provider state
- **WHEN** native input contains authenticated redacted thinking or Claude-hosted search state
- **THEN** it returns nonportable_provider_history at the affected input index and retains the original data

#### Scenario: Native history stays native
- **WHEN** native reasoning with valid rs-prefixed identity and encrypted content is replayed
- **THEN** its encryption remains intact and no Claude projection occurs

#### Scenario: Plaintext reasoning preservation
- **WHEN** a reasoning item carries both an existing summary and distinct reasoning_text content
- **THEN** native sanitation retains both texts as summaries and empties the content array

### Requirement: Foreign reasoning at Claude dispatch

Translated Claude Responses SHALL classify provider-specific reasoning before signed-history authentication and account selection. Completed foreign reasoning with readable summary or reasoning_text content SHALL become ordinary historical assistant text, preserving distinct text and ordering without ciphertext, lookup IDs or fabricated thinking signatures. Completed foreign encrypted reasoning without readable text SHALL produce no Claude wire block, without blocking the surrounding portable conversation. Plaintext-only reasoning SHALL follow the same portable projection. Logical retained history, user/assistant messages and tool pairing MUST remain unchanged. Input positions SHALL remain stable for indexed diagnostics. The policy SHALL apply after expansion to HTTP and WebSocket, including replayed continuation.

Foreign encrypted reasoning in the active turn MUST fail before dispatch with nonportable_provider_history and the affected input index. A paired tool output MUST NOT count as a new user turn. Complete-history compaction SHALL apply the same rule to the client-supplied history, excluding its summarization instruction: a history ending with an assistant message is a closed turn with no active reasoning; otherwise the active turn starts at the last user or external task input. Purely plaintext compaction SHALL preserve all readable reasoning. Genuine Claude envelopes, including empty-display signed blocks, MUST retain existing client/conversation authentication and account/model ownership. Authentication failures SHALL expose invalid_provider_history with an input index rather than a generic payload message. Conversion and opaque-omission diagnostics MUST contain counts only, never reasoning or opaque contents.

#### Scenario: Sol-to-Opus historical switch
- **WHEN** completed OpenAI reasoning has a readable summary and encrypted_content before a new user message
- **THEN** Claude receives the summary as historical assistant text, no foreign ciphertext or synthetic thinking, and retained history remains unchanged

#### Scenario: Opaque-only history
- **WHEN** completed foreign encrypted reasoning has no readable summary or content
- **THEN** Claude receives the surrounding portable messages and tool pairs without that private reasoning block
- **AND** retained history keeps its original ciphertext and item ordering for native replay

#### Scenario: Active foreign tool continuation
- **WHEN** foreign encrypted reasoning belongs to the active assistant turn and is followed only by paired tool output
- **THEN** preparation fails explicitly instead of fabricating a signed continuation

#### Scenario: Complete compaction
- **WHEN** a Claude compact request contains foreign encrypted reasoning before the last user input, or in a closed turn ending with an assistant message
- **THEN** it summarizes the readable conversation without foreign ciphertext, exactly as a normal turn would project it

#### Scenario: Compaction inside an open foreign tool loop
- **WHEN** a Claude compact request ends in tool output of a turn whose foreign encrypted reasoning follows the last user input
- **THEN** it fails with nonportable_provider_history at that input index without upstream dispatch
- **AND** a plaintext-only history can compact with all its readable reasoning

#### Scenario: Mixed-provider round trip
- **WHEN** completed Claude signed state and readable or opaque-only OpenAI history are replayed to their authorized original Claude model/account
- **THEN** genuine Claude blocks remain verbatim, foreign readable reasoning becomes text, and completed opaque-only foreign state produces no Claude block

#### Scenario: Fork or tampering
- **WHEN** a Claude envelope has a foreign client/conversation scope or invalid authentication
- **THEN** invalid_provider_history identifies the original input index before upstream dispatch without weakening scope checks

### Requirement: Automatic Claude subscription discovery
Explicit credential imports SHALL preserve non-secret subscriptionType and
rateLimitTier. Account responses SHALL expose a derived Free, Pro, Max, Max 5x,
Max 20x, Team, Enterprise or Unknown plan. Known specific rate-limit tiers SHALL
take priority over generic subscription type. Absent or unsupported identifiers
MUST NOT imply Free, Max 20x, quota capacity or model entitlement.

#### Scenario: Imported Max multiplier
- **WHEN** an imported credential reports subscriptionType max and rateLimitTier default_claude_max_5x
- **THEN** the account displays Max 5x without changing routing or quota limits

### Requirement: Coordinated subscription metadata refresh
The gateway SHALL read /api/claude_cli/bootstrap with its maintained Claude CLI
management headers and validate the authenticated account and organization.
Subscription polling SHALL use independent durable claims, six-hour successful
cadence, generation fencing and existing metadata Retry-After cooldowns. Manual
refresh MUST NOT bypass cooldowns or claims. Existing accounts SHALL participate
without reimport. Failures SHALL retain last-known subscription metadata and
timestamps and expose a safe diagnostic without changing inference health.

#### Scenario: Account upgrade
- **WHEN** authenticated bootstrap changes an imported Pro subscription to Max 20x
- **THEN** the retained metadata and displayed plan become Max 20x

#### Scenario: Failed discovery
- **WHEN** bootstrap returns 429 or malformed metadata
- **THEN** last-known metadata is retained and cooldown applies independently of catalog and usage

#### Scenario: Identity or generation mismatch
- **WHEN** bootstrap identifies another account or the credential generation changes during its fetch
- **THEN** the response cannot overwrite the enrolled account's subscription

### Requirement: Claude plan presentation
Claude cards, account lists and details SHALL show localized plan labels in
existing account subtitle styling. Provider labels SHALL say Claude, without an
OAuth suffix; authentication-method controls SHALL remain distinct. Account search SHALL match the detected plan.
Unknown data SHALL remain explicit; detail diagnostics SHALL identify failed
subscription refreshes without exposing tokens or raw upstream bodies.

#### Scenario: Unknown subscription
- **WHEN** an account has no recognized subscription metadata
- **THEN** the account subtitle shows an unknown plan rather than a guessed tier

### Requirement: Claude request plan snapshots
Claude native Messages, token counts, translated Responses and Chat requests SHALL
record the selected account's normalized subscription at dispatch preparation.
Successful and failed attempts SHALL retain that snapshot through settlement,
including downstream WebSocket requests and account failover. Request tables and
details SHALL display the same localized plan labels as accounts. Historical
rows lacking a snapshot MUST NOT be relabeled using current account metadata.

#### Scenario: Subscription changes during inference
- **WHEN** a Pro account becomes Max 20x while a prepared request is running
- **THEN** that request log still shows Pro and subsequent preparations show Max 20x

#### Scenario: No known subscription
- **WHEN** a Claude request is prepared without recognized subscription metadata
- **THEN** its log records Unknown, distinct from historical rows without a plan

### Requirement: History-preserving translated Claude continuation
Translated Claude requests ending in an assistant message SHALL append one wire-only user `(continue)` turn after validating complete tool results. Existing history and signed blocks MUST remain ordered and unchanged. User-ending requests, native Messages and retained logical history MUST remain unchanged. This transformation MUST NOT relax authentication or resource ownership.

#### Scenario: Retry after assistant progress
- **WHEN** Codex retries an interrupted response with history ending in assistant progress
- **THEN** Claude receives all original history followed by a user continuation rather than assistant prefill
- **AND** no prior message is removed and the synthetic turn is not retained as client input

#### Scenario: Expanded continuation
- **WHEN** previous_response_id expands to completed assistant output with no new input
- **THEN** Claude receives one user continuation after the expanded output

#### Scenario: Unfinished tool call
- **WHEN** the input ends with a tool call lacking its corresponding result
- **THEN** preparation fails before dispatch without fabricating tool output or appending a continuation

#### Scenario: Existing user or tool-result ending
- **WHEN** translated input already ends with user content or a validated tool result
- **THEN** no continuation text is added

#### Scenario: Native request
- **WHEN** a native Messages client submits assistant-tail history
- **THEN** the gateway does not apply this translated-request continuation policy

### Requirement: Bounded undeclared Claude tool diagnostics
Undeclared upstream Claude tools SHALL fail explicitly without alias guessing or client-side execution. Diagnostics SHALL identify source, model, response, content index, declaration count and a bounded name fingerprint; a bounded syntactically safe tool name MAY also be recorded. Arguments, call IDs, conversation contents and credentials MUST NOT be logged.

#### Scenario: Unknown tool after text
- **WHEN** Claude emits an undeclared tool after an assistant progress message
- **THEN** the tool is rejected with content-free identity diagnostics and no tool-call event for that tool reaches the client

#### Scenario: Unsafe name
- **WHEN** the rejected name contains control characters, unsupported characters or excessive length
- **THEN** only its fingerprint and safe structural metadata are logged
