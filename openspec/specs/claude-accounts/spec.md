# Claude Accounts

## Purpose

Provide separately owned Claude OAuth credentials and faithful native and adapted inference without an intermediate gateway.

## Requirements

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
remove only completed historical thinking, preserve active ordinary and server
tool cycles, and leave all visible content and tool pairs unchanged. If removal
would leave an empty message or no safe change exists, it SHALL return the error.
Generic errors, 429s and latest-assistant-modification errors MUST NOT trigger it.

#### Scenario: Historical rejection
- **WHEN** an upstream rejects an eligible historical thinking signature
- **THEN** one same-target recovery attempt is allowed, without changing accounts

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
Only explicitly selected available models on enabled, credential-healthy and client-authorized accounts SHALL be routed. Catalog synchronization MUST paginate atomically and retain the previous snapshot on failure. Quota monitoring SHALL represent observed shared and model-specific windows and unknown/stale state truthfully. Pool attempts MUST preserve model, opaque-state ownership, admission and exactly-once settlement; no retry SHALL occur after visible output or ambiguous dispatch.

#### Scenario: Model-specific exhaustion
- **WHEN** an account has an exhausted model-specific window
- **THEN** that account is ineligible for that model without disabling unrelated models

#### Scenario: Unavailable continuation owner
- **WHEN** account-bound continuation names a paused, unauthorized, refreshing or quota-exhausted owner
- **THEN** selection returns an explicit owner-unavailable error without choosing another account

#### Scenario: Worker-independent affinity
- **WHEN** the same client scope, conversation, model and eligible pool are evaluated by separate workers
- **THEN** account selection agrees regardless of database row order

#### Scenario: Missing quota and entitlement information
- **WHEN** quota monitoring omits a window or returns null
- **THEN** the dashboard represents it as unknown, not zero usage or a denied model entitlement

#### Scenario: Stale exhausted quota
- **WHEN** an exhausted window has a future reset but monitoring has become stale
- **THEN** its known exhaustion continues to block applicable models until reset or a newer observation
- **AND** passing its reset changes the observation to unknown rather than fabricating zero usage

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
The gateway SHALL authenticate historical Claude state against client and conversation before routing. Completed thinking SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking from outbound projection while preserving visible text and paired tools and leaving retained history unchanged. It SHALL record an omission count without content or credentials. Active reasoning and server search SHALL remain account/model-bound. A subsequent explicit user message, not a tool output, SHALL mark earlier thinking completed. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active reasoning

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
Selection SHALL distinguish quota-only exhaustion from other unavailability within the authorized model/owner scope. Quota-only exhaustion SHALL return429; mixed or unknown unavailability SHALL retain503. Known candidate recovery SHALL account for every applicable temporary barrier, using the latest deadline per candidate and earliest across fully known candidates. Unknown deadlines MUST NOT be fabricated. Hard owner errors SHALL retain their code and scope. HTTP errors SHALL include a ceil-rounded positive Retry-After when justified. Actual exhausted upstream errors and local admission contracts SHALL remain unchanged.

#### Scenario: Multiple restrictions
- **WHEN** one candidate has quota reset in two hours and model cooldown in five, and another recovers in three
- **THEN** the reported known recovery delay is three hours

#### Scenario: Known exhaustion without a deadline
- **WHEN** all candidates are quota-exhausted but no candidate has a complete recovery deadline
- **THEN** the response remains429 without a fabricated Retry-After

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
