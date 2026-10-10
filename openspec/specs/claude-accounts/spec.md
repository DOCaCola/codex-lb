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
Claude SHALL support Responses over downstream HTTP and WebSocket while using HTTPS/SSE upstream. Translation MUST preserve portable text, tool/custom-tool/namespace, image, reasoning and cache-usage semantics, or reject unsupported semantics explicitly. A custom tool with a lark or regex grammar format SHALL be projected as a single raw-text input whose description carries the grammar; the client remains responsible for validating that input. Claude catalog models SHALL advertise the freeform patch tool type. Truncation, `model_context_window_exceeded` and pause_turn MUST NOT become completed; they SHALL surface as incomplete with reason max_output_tokens. A refusal stop reason MUST NOT become completed or incomplete; for every translated projection it SHALL fail as `response.failed` with error code `invalid_prompt` and a message naming the refusal category and Claude's explanation, preserving usage, so clients end the turn without retrying. Non-streaming translated Responses and Chat SHALL return HTTP 400 `invalid_request_error` with that error, and streaming Chat SHALL emit it as an error event; refused output SHALL follow the refused-output requirement. A refusal MAY end the stream while content blocks or search calls are still open; that partial output SHALL be discarded: it MUST NOT receive done events and MUST NOT appear in the terminal output or continuation history, so an unfinished tool call is never delivered as executable or replayed without a result. Native passthrough SHALL forward such a refusal unchanged and record it as an incomplete terminal. Any other stop with open content, pending search calls or no stop reason SHALL fail with a message naming the open block types, pending search count and stop reason. Each translated message stop, including a malformed one logged with status `invalid`, SHALL log its stop reason, resulting status, upstream content block type counts, output tokens, a bounded refusal category when Claude supplies one, the withheld item count and whether output was delivered, never content, reasoning, tool input, signatures or refusal explanations. A Claude transport failure SHALL name its exception class. Durable continuation MUST be persisted before terminal delivery and scoped to compatible account/model state; compaction MUST preserve useful context.

#### Scenario: Pause turn
- **WHEN** Anthropic stops with pause_turn
- **THEN** the Responses client receives an incomplete result with reason max_output_tokens and no hidden automatic continuation

#### Scenario: Context window exhausted
- **WHEN** Anthropic stops with model_context_window_exceeded
- **THEN** the client receives an incomplete result with reason max_output_tokens, never a completed result or an unknown-stop error

#### Scenario: Refusal
- **WHEN** Anthropic stops with refusal on a translated Responses or Chat request, with or without visible reasoning
- **THEN** the response fails with error code invalid_prompt, a message naming the refusal category, and the turn's usage, so Codex does not retry it

#### Scenario: Non-streaming refusal
- **WHEN** Anthropic refuses a non-streaming translated Responses or Chat request
- **THEN** the client receives HTTP 400 invalid_request_error with code invalid_prompt

#### Scenario: Mid-stream refusal with an open tool call
- **WHEN** Anthropic stops with refusal while a tool call block is still open
- **THEN** the client receives no done event for that call, the terminal output omits it, and the response fails with invalid_prompt

#### Scenario: Native mid-stream refusal
- **WHEN** a native Messages stream stops with refusal while a content block is open
- **THEN** the stream is forwarded unchanged and settled as an incomplete terminal

#### Scenario: Unfinished non-refusal stop
- **WHEN** a stream stops with an open block or pending search under any other stop reason, or without a stop reason
- **THEN** the request fails with a message naming the open block types, pending search count and stop reason, and the stop diagnostic line is logged

#### Scenario: Stop diagnostics
- **WHEN** a translated Claude message stops
- **THEN** one log line records the stop reason, status, block type counts, output tokens, refusal category, withheld count and delivered-output flag without any content or refusal explanation

#### Scenario: Transport drop
- **WHEN** the Claude connection fails before message_stop
- **THEN** the failure message names the transport exception class

#### Scenario: Grammar-format custom tool
- **WHEN** a Responses request declares a custom tool with a lark or regex grammar, such as Codex's apply_patch
- **THEN** Claude receives a tool with one required string input documenting that grammar, and its call returns to the client as a custom_tool_call carrying the raw input

#### Scenario: Patch tool advertisement
- **WHEN** a Codex client reads the model catalog
- **THEN** Claude models advertise apply_patch_tool_type freeform so the client registers its patch tool

#### Scenario: Unsupported constrained output
- **WHEN** a Responses request declares a malformed grammar, an unknown custom tool format or a provider-specific control without a Claude equivalent
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
Translated Claude Responses SHALL accept nameless web_search declarations and map supported live search options to native Anthropic search. A declaration with external_web_access=false SHALL be omitted, allowing conversation to continue without granting cached or live search through that tool. Other unsupported options MUST fail before dispatch rather than silently weaken caller constraints. HTTP and WebSocket Responses SHALL expose search lifecycle and URL citations, preserve real upstream search state across continuation, and reject missing, tampered or cross-account/model/client replay state. Server search errors and unfinished searches MUST NOT become successful completion.

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
Translated Responses SHALL produce deterministic ephemeral cache boundaries for stable instruction/tool prefixes and recent user history, within Anthropic's four-breakpoint limit. Proxy-generated boundaries SHALL use the 1-hour tier (`ttl: "1h"`) that Claude Code sends, and translated requests SHALL negotiate `extended-cache-ttl-2025-04-11`. All proxy-generated boundaries share that tier, so no longer TTL follows a shorter one. Native caller markers, native betas and signed server content MUST remain unchanged. Projection MUST NOT mutate retained logical history.

#### Scenario: Subsequent translated turn
- **WHEN** a translated conversation adds another user turn
- **THEN** stable prefix and recent user-turn cache boundaries are present without changing prior text or signed blocks

#### Scenario: Translated boundaries survive agent pauses
- **WHEN** a translated request is prepared
- **THEN** every proxy-generated boundary is `{"type":"ephemeral","ttl":"1h"}`
- **AND** the request's `anthropic-beta` includes `extended-cache-ttl-2025-04-11`

#### Scenario: Native markers are not upgraded
- **WHEN** a native Claude Code request carries its own cache markers
- **THEN** those markers and the caller's TTLs are forwarded unchanged

### Requirement: Translated completed reasoning recovery
The gateway SHALL authenticate historical Claude state against the client scope before routing. Conversation identity SHALL govern session identity, routing affinity and retained continuation but MUST NOT authorize history, so a forked or other conversation of the same client SHALL replay authenticated state under the same model and account ownership rules. Completed thinking and completed server search SHALL provide only a preferred eligible account. When the selected account or model differs, the gateway SHALL omit incompatible completed thinking and project incompatible completed search as portable hosted-search history, while preserving visible text and paired tools and leaving retained history unchanged. Compaction SHALL instead project completed thinking as readable historical assistant text, omit only redacted thinking and project completed search the same way. It SHALL record conversion, omission and search-projection counts without content or credentials. Active reasoning and active server search SHALL remain account/model-bound. A subsequent explicit user message or canonical external task input, not a paired tool output, SHALL mark earlier thinking and search completed; compaction SHALL determine this on the client-supplied history excluding its summarization instruction. Invalid authentication or conflicting strict owners MUST fail before dispatch.

#### Scenario: Historical account unavailable
- **WHEN** only completed thinking belongs to an unavailable account
- **THEN** an eligible alternative can serve the visible conversation without replaying incompatible opaque thinking

#### Scenario: Model switch
- **WHEN** completed thinking belongs to another model
- **THEN** the requested model receives portable visible history without that thinking

#### Scenario: Completed search on another route
- **WHEN** completed server search belongs to another model or an unavailable account
- **THEN** the selected route receives the projected search text without the original call and encrypted result

#### Scenario: Compaction on another route
- **WHEN** compaction selects another account or model than completed thinking
- **THEN** the summarizer receives that thinking as readable assistant text in its original position, without a signature

#### Scenario: Active tool cycle
- **WHEN** incompatible reasoning or server search belongs to the active tool turn
- **THEN** preparation fails rather than dropping required active state

#### Scenario: Authenticated Chat tool cycle
- **WHEN** a keyed Chat client resends the complete visible history and all tool results for one live Claude tool response
- **THEN** the gateway restores only that response's genuine signed or redacted thinking under the same client, model and account owner
- **AND** unavailable or ambiguous replay SHALL reconstruct only caller-visible, representable Chat tool history without copying authenticated opaque state or fabricating signatures

#### Scenario: Authentication boundary
- **WHEN** an envelope is tampered or belongs to another client
- **THEN** preparation fails before upstream dispatch

#### Scenario: Forked conversation
- **WHEN** a forked conversation of the same client replays genuine envelopes minted under its parent conversation
- **THEN** authentication succeeds without fork metadata, completed thinking and search keep only their account preference, and active reasoning and search keep their original model and account owner

### Requirement: Synthesized identity coherence
Translated Messages SHALL include a stable local device identity and the same scoped session identity in body metadata and headers. Session metadata on every outbound Messages request that carries it SHALL name the authenticated provider account UUID of the serving account; a client-supplied account UUID MUST NOT be forwarded to another account, and an unauthenticated account identity MUST NOT be fabricated. The provider account UUID SHALL be persisted from the authenticated profile and checked against the enrolled identity before use. Synthesized OS and architecture SHALL match the runtime; native reviewed headers SHALL remain caller-owned. No billing fingerprint SHALL be synthesized.

#### Scenario: Rotated credentials
- **WHEN** the selected account refreshes its token within the same client conversation
- **THEN** local device and session metadata remain stable without reusing identity across another client or account

#### Scenario: Pooled native request
- **WHEN** a native Claude Code request carrying its own account UUID is served by a different pooled account
- **THEN** the outbound metadata names the serving account's UUID and preserves the remaining client metadata

#### Scenario: Account enrolled before UUID persistence
- **WHEN** an enrolled account without a stored provider UUID next uses its credentials
- **THEN** its authenticated profile is checked against the enrolled identity and the UUID is stored, or the request fails if the identity differs

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

Window freshness and provenance SHALL distinguish header receipt from polling. Header updates MUST NOT mark unrelated windows fresh, clear poll errors, erase model-specific windows or clear refusal cooldowns. Request-start ordering SHALL prevent older concurrent requests from replacing newer observations; expired evidence SHALL be unknown. Atomic bounded merges SHALL preserve concurrent settings/catalog updates. History SHALL record every sample whose utilization or reset deadline differs from the latest stored sample for that account/window; unchanged samples SHALL be bounded to one per account/window/minute. Observation failures MUST NOT fail or retry inference; cancellation and upstream ownership SHALL remain intact.

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

#### Scenario: Exhaustion within the sampling minute
- **WHEN** five-hour utilization moves from 99% to 100% 27 seconds after the 99% sample with the same reset deadline
- **THEN** history stores the 100% sample
- **AND** a repeated 100% sample within the same minute is not stored

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
Selection SHALL distinguish quota-only exhaustion from other unavailability within the authorized model/owner scope. Quota-only exhaustion SHALL return429, including a required continuation owner; mixed or unknown unavailability SHALL retain503. Known candidate recovery SHALL account for every applicable temporary barrier, using the latest deadline per candidate and earliest across fully known candidates. Unknown deadlines MUST NOT be fabricated. Hard owner errors SHALL retain their code and scope. Quota refusals SHALL identify observed blocking windows without exposing account identities or history. HTTP errors SHALL include a ceil-rounded positive Retry-After when justified. Known recovery SHALL include resets_at as integer Unix seconds rounded up and resets_in_seconds in public error details; downstream Responses WebSocket errors SHALL preserve those details, status and safe Retry-After. Quota-only refusals SHALL use error type `usage_limit_reached` on OpenAI-envelope surfaces, which Codex presents as a usage limit with its reset time, and `rate_limit_error` on native Anthropic Messages surfaces. They MUST NOT carry `plan_type`. Actual exhausted upstream errors and local admission contracts SHALL remain unchanged.

#### Scenario: Multiple restrictions
- **WHEN** one candidate has quota reset in two hours and model cooldown in five, and another recovers in three
- **THEN** the reported known recovery delay is three hours

#### Scenario: Known exhaustion without a deadline
- **WHEN** all candidates are quota-exhausted but no candidate has a complete recovery deadline
- **THEN** the response remains429 without a fabricated Retry-After or reset fields

#### Scenario: Quota-blocked continuation owner
- **WHEN** active signed history or server resources require a quota-exhausted account and another account is eligible
- **THEN** a Responses client receives429 usage_limit_reached with previous_response_owner_unavailable, observed blocking windows and only the owner's known recovery timing
- **AND** no alternate account is dispatched and retained history remains unchanged

#### Scenario: Native quota refusal
- **WHEN** a native Messages request is refused for quota only
- **THEN** it receives an Anthropic error envelope with429 rate_limit_error and the same reset fields

#### Scenario: Non-quota continuation owner
- **WHEN** the required owner is paused, unauthorized, refreshing or blocked by unknown cooldown evidence
- **THEN** the owner error remains503 without becoming a quota-only refusal

#### Scenario: WebSocket quota refusal
- **WHEN** a downstream Responses WebSocket turn has a quota-only owner exclusion
- **THEN** its error frame carries status429, usage_limit_reached, the owner code and available reset fields and retry-after header without leaking credentials

### Requirement: Native resource provenance
Native server-tool history SHALL resolve its authorized source from observed
resource origins, independently of soft session affinity. Origins SHALL be
scoped to client and model, retained for thirty days of authorized
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

#### Scenario: Forked native session
- **WHEN** a forked native session of the same client replays a retained server resource
- **THEN** the request selects the resource's original origin account

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
Known budget-thinking models SHALL advertise reasoning separately from adaptive-thinking models. Requested efforts SHALL map to a documented budget below the effective output cap, and impossible explicit caps SHALL fail before upstream dispatch. Translated requests SHALL reject unsupported sampling controls when thinking is enabled before dispatch. Omitted/off reasoning SHALL not enable thinking. Request logs SHALL distinguish requested effort from effective upstream effort, thinking mode and budget when applicable across native Messages and translated Responses, Chat and WebSocket routes, without inferring effort from a native budget. Upstream effort and thinking mode SHALL record the values sent upstream; when the upstream request leaves either to the provider's model-dependent default, it SHALL be recorded as unset rather than inferred. Explicit null sampling controls SHALL be treated as absent.

#### Scenario: Thinking left to the model default
- **WHEN** a Claude request is dispatched without a `thinking` block or `output_config.effort`
- **THEN** its request log records upstream thinking mode and upstream effort as unset, not as disabled or a guessed default

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
Canonical external task input SHALL count as a new user turn when classifying completed versus active signed thinking and server search, using the same classifier as protocol projection. All opaque blocks MUST be authenticated before omission or projection. Tool results and malformed task envelopes MUST NOT close active thinking or search. Server resource state SHALL retain its existing strict account/model ownership. Rejected tool-output diagnostics SHALL include identifier presence/type and metadata completeness without raw metadata or content.

#### Scenario: Completed thinking before a new task
- **WHEN** authenticated thinking precedes canonical external task input and the target account/model changes
- **THEN** only completed thinking may be omitted under the existing replay policy, and task content remains intact

#### Scenario: Search ownership is not relaxed by a task
- **WHEN** canonical external task input follows Claude search history and the target account/model changes
- **THEN** that search is completed and is projected as portable hosted-search history
- **AND** its call and encrypted result are still sent only to their original owner and model

#### Scenario: Search inside an active tool cycle
- **WHEN** Claude search belongs to a turn that only paired tool output follows
- **THEN** it still requires the original owner and model on another Claude route

### Requirement: Claude history at native Codex dispatch

Native Codex dispatch SHALL authenticate replayed Claude envelopes against the originating client before projecting history. Authenticated Claude thinking and redacted thinking SHALL be omitted, because OpenAI accepts reasoning only as its own encrypted state and refuses to chain onto a response that stored unverifiable reasoning. Claude encryption, signatures, thinking text and foreign lookup identities MUST NOT reach OpenAI. Projection SHALL leave retained logical history, messages, tool call identifiers and paired outputs unchanged. The same policy SHALL apply to HTTP, WebSocket, retained continuation and native compaction.

Native sanitation SHALL forward a `reasoning` item only when it carries non-empty `encrypted_content`; any other reasoning item, including summary-only and plaintext reasoning from another provider, SHALL be omitted. Kept items SHALL have plaintext `content` cleared and output-only `status` removed while their encryption and summary stay intact. Sanitation SHALL remove invalid known item-type ID prefixes without fabricating identities and reject unprojected Claude envelopes. Authenticated Claude-hosted search SHALL follow portable hosted-search history projection. These rules SHALL apply in completed and active turns. Projection diagnostics SHALL count omitted thinking, omitted unverifiable reasoning and projected searches without content. Authentication failures MUST NOT dispatch or penalize an upstream account.

#### Scenario: Opus-to-Sol switch
- **WHEN** a scoped Claude thinking envelope with a resp_msg-prefixed reasoning ID is replayed to native Sol
- **THEN** OpenAI receives the surrounding history without that item, and neither its Claude envelope, its text nor its foreign ID
- **AND** the original retained item remains unchanged

#### Scenario: Chained turn after a switch
- **WHEN** the first native turn after a switch from Claude succeeds and the next turn chains onto it with `previous_response_id`
- **THEN** the stored response contains no reasoning that OpenAI cannot verify

#### Scenario: Tool continuation
- **WHEN** Claude thinking accompanies a complete function/custom-tool call and result pair
- **THEN** native projection preserves their identifiers, arguments and outputs in order

#### Scenario: Tampered or cross-scope envelope
- **WHEN** Claude state is invalid or belongs to another client
- **THEN** the native request fails before upstream dispatch without exposing state contents

#### Scenario: Unrepresentable provider state
- **WHEN** native input contains authenticated Claude redacted thinking
- **THEN** OpenAI receives the surrounding history without that item, the omission is counted, and retained history keeps the original

#### Scenario: Claude hosted search
- **WHEN** native input contains an authenticated Claude search envelope and its `web_search_call`
- **THEN** OpenAI receives one projected assistant text message in their place, and neither the envelope nor the Claude call identity

#### Scenario: Native history stays native
- **WHEN** native reasoning with valid rs-prefixed identity and encrypted content is replayed
- **THEN** its encryption and summary remain intact and no Claude projection occurs

#### Scenario: Foreign plaintext reasoning
- **WHEN** a reasoning item without `encrypted_content` carries a summary or reasoning_text content
- **THEN** native sanitation omits it and counts the omission

#### Scenario: Plaintext reasoning preservation
- **WHEN** a reasoning item with `encrypted_content` also carries reasoning_text content
- **THEN** native sanitation keeps its encryption and existing summary, empties the content array, and does not move the plaintext into the summary

### Requirement: Foreign reasoning at Claude dispatch

Translated Claude Responses SHALL classify provider-specific reasoning before signed-history authentication and account selection. Foreign reasoning with readable summary or reasoning_text content SHALL become ordinary assistant text, preserving distinct text and ordering without ciphertext, lookup IDs or fabricated thinking signatures. Foreign encrypted reasoning without readable text SHALL produce no Claude wire block, without blocking the surrounding portable conversation. Plaintext-only reasoning SHALL follow the same portable projection. This projection SHALL apply equally to completed turns and the active turn, including an open tool loop. Logical retained history, user/assistant messages and tool pairing MUST remain unchanged. Input positions SHALL remain stable for indexed diagnostics. The policy SHALL apply after expansion to HTTP and WebSocket, including replayed continuation.

A paired tool output MUST NOT count as a new user turn. Complete-history compaction SHALL project the client-supplied history the same way, excluding its summarization instruction. Genuine Claude envelopes, including empty-display signed blocks, MUST retain existing client authentication and account/model ownership. Authentication failures SHALL expose invalid_provider_history with an input index rather than a generic payload message. Projection diagnostics MUST contain counts only, including how many projected items belong to the active turn, never reasoning or opaque contents.

#### Scenario: Sol-to-Opus historical switch
- **WHEN** completed OpenAI reasoning has a readable summary and encrypted_content before a new user message
- **THEN** Claude receives the summary as historical assistant text, no foreign ciphertext or synthetic thinking, and retained history remains unchanged

#### Scenario: Opaque-only history
- **WHEN** completed foreign encrypted reasoning has no readable summary or content
- **THEN** Claude receives the surrounding portable messages and tool pairs without that private reasoning block
- **AND** retained history keeps its original ciphertext and item ordering for native replay

#### Scenario: Active foreign tool continuation
- **WHEN** foreign encrypted reasoning belongs to the active assistant turn and is followed only by paired tool output
- **THEN** Claude receives its readable text, the tool call and the tool result without foreign ciphertext or synthetic thinking
- **AND** the projection log counts the item as active

#### Scenario: Complete compaction
- **WHEN** a Claude compact request contains foreign encrypted reasoning before the last user input, or in a closed turn ending with an assistant message
- **THEN** it summarizes the readable conversation without foreign ciphertext, exactly as a normal turn would project it

#### Scenario: Compaction inside an open foreign tool loop
- **WHEN** a Claude compact request ends in tool output of a turn whose foreign encrypted reasoning follows the last user input
- **THEN** it summarizes the readable conversation without foreign ciphertext, exactly as a normal turn would project it
- **AND** a plaintext-only history can compact with all its readable reasoning

#### Scenario: Mixed-provider round trip
- **WHEN** completed Claude signed state and readable or opaque-only OpenAI history are replayed to their authorized original Claude model/account
- **THEN** genuine Claude blocks remain verbatim, foreign readable reasoning becomes text, and opaque-only foreign state produces no Claude block

#### Scenario: Fork or tampering
- **WHEN** a Claude envelope minted in a parent conversation of the same client is replayed by a fork
- **THEN** it authenticates and dispatch follows the normal model and account ownership rules
- **AND** an envelope with a foreign client scope or invalid authentication returns invalid_provider_history identifying the original input index before upstream dispatch

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
Claude tool calls SHALL resolve by wire name, or by the client's own qualified tool name when exactly one tool in the request has it. Other names, including a client name shared by several tools, SHALL fail explicitly without further alias guessing or client-side execution. Diagnostics SHALL identify source, model, response, content index, declaration count and a bounded name fingerprint; a bounded syntactically safe tool name MAY also be recorded. Arguments, call IDs, conversation contents and credentials MUST NOT be logged.

#### Scenario: Unknown tool after text
- **WHEN** Claude emits an undeclared tool after an assistant progress message
- **THEN** the tool is rejected with content-free identity diagnostics and no tool-call event for that tool reaches the client

#### Scenario: Unsafe name
- **WHEN** the rejected name contains control characters, unsupported characters or excessive length
- **THEN** only its fingerprint and safe structural metadata are logged

#### Scenario: Client name used by Claude
- **WHEN** Claude calls `write_stdin` and the request declared exactly one tool with that name
- **THEN** the call resolves to that tool

#### Scenario: Ambiguous client name
- **WHEN** Claude calls a client name that several declared tools share
- **THEN** the call is rejected as undeclared

### Requirement: Translated thinking retention
Translated Responses whose projected `thinking.type` is `enabled` or `adaptive` SHALL send `context_management: {"edits":[{"type":"clear_thinking_20251015","keep":"all"}]}` and negotiate `context-management-2025-06-27`, as Claude Code does, so earlier-turn thinking stays in the cached prefix across user turns. Translated requests with any other or absent thinking value MUST NOT send the edit or that beta for it. Native requests MUST forward the caller's body and betas unchanged.

#### Scenario: New user turn keeps the cached prefix
- **WHEN** a translated request with adaptive thinking replays signed thinking from an earlier turn
- **THEN** its body carries the keep-all thinking edit and its `anthropic-beta` includes `context-management-2025-06-27`

#### Scenario: Thinking disabled
- **WHEN** a translated request has no thinking or thinking `disabled`
- **THEN** no `context_management` is sent

#### Scenario: Native request
- **WHEN** a native Claude Code request is forwarded
- **THEN** its `context_management` and betas are those the caller sent

### Requirement: Translated tool calls declare plaintext arguments
When a translated Claude function call targets a tool whose declaration marks any parameter `encrypted`, every public Responses representation of that call (streamed added and done items and final output, over HTTP and WebSocket) SHALL carry `encrypted_function_args: []`. Calls to tools without encrypted parameters and custom tool calls SHALL NOT carry the field.

#### Scenario: Subagent spawn from Claude
- **WHEN** Claude calls the collaboration `spawn_agent` tool whose `message` parameter is declared encrypted
- **THEN** the client receives the call with `encrypted_function_args: []` and delivers the message to the child as plaintext

#### Scenario: Ordinary tool
- **WHEN** Claude calls a function whose parameters declare no encryption
- **THEN** the call carries no `encrypted_function_args` field

### Requirement: Inter-agent messages are Claude user turns
Translated Claude Responses requests SHALL accept `agent_message` items whose content is plaintext and project them as user turns, under the same tool-cycle rules as user messages. The turn SHALL carry the item's content unchanged; Codex's agent-message header naming the recipient and sender is part of that content, and the proxy MUST NOT add another. An `agent_message` with an `encrypted_content` part SHALL fail with `nonportable_agent_message` and SHALL NOT be dropped or forwarded as text.

#### Scenario: Child progress wakes a Claude parent
- **WHEN** a Claude parent's history contains a plaintext `agent_message` from its child after a completed tool cycle
- **THEN** Claude receives the message content, including Codex's header, exactly once as a user turn

#### Scenario: Pre-deployment encrypted message
- **WHEN** the history contains an `agent_message` with OpenAI ciphertext
- **THEN** the request fails with `nonportable_agent_message`

### Requirement: Streamed tool calls without arguments keep their declared input
The Claude Responses stream projection SHALL treat an empty `input_json_delta` fragment as carrying no input: it SHALL NOT be buffered or forwarded as a client argument delta. When a tool block streams no argument JSON, its input SHALL be the `input` from `content_block_start` and SHALL be decoded and validated exactly as a non-streamed block. Non-empty argument JSON that does not parse SHALL fail the response.

#### Scenario: Function tool without arguments
- **WHEN** Claude starts a function tool block with input `{}` and streams only an empty argument fragment
- **THEN** the client receives a completed `function_call` with arguments `{}` and no empty argument delta

#### Scenario: Wrapped tool without arguments
- **WHEN** a tool whose schema needs the arguments envelope streams no argument JSON
- **THEN** the response fails with the tool's invalid arguments envelope error

#### Scenario: Malformed argument JSON
- **WHEN** a tool block streams non-empty argument JSON that does not parse
- **THEN** the response fails with an invalid tool JSON error

### Requirement: Claude accounts are listed by name
The Claude account API SHALL return accounts ordered by account name, with the source ID breaking ties.

#### Scenario: Several Claude accounts
- **WHEN** Claude accounts named Zulu, Alpha and Mike exist
- **THEN** the account list returns Alpha, Mike, Zulu

### Requirement: Bounded Claude pre-dispatch connection recovery
A Claude send whose connection failed before any request byte was dispatched (DNS resolution, connection refusal, connect timeout or proxy connect failure) MAY be retried on the same account. TLS verification failures and every failure after connection establishment MUST NOT be retried. Retries SHALL consume the shared four-send budget and fit the same ten-second recovery window as overload recovery. Each wait SHALL be jittered and grow per retry, starting at 250–500ms, and SHALL be cancellable and own no admission or reservation. Repreparation SHALL enforce current authorization and history ownership. Pre-dispatch recovery MUST NOT refresh credentials, rotate accounts, record cooldowns or penalize account or provider health. Exhaustion SHALL return the last connection failure.

#### Scenario: Transient DNS failure
- **WHEN** the first send fails with a DNS resolution error and the next send connects
- **THEN** the request completes on the same account without the client observing the failure

#### Scenario: TLS verification failure
- **WHEN** the send fails TLS certificate verification
- **THEN** the failure is returned without a retry

#### Scenario: Ambiguous network failure
- **WHEN** the connection drops after the request was dispatched
- **THEN** the gateway does not replay the request

#### Scenario: Persistent outage
- **WHEN** every send fails before dispatch
- **THEN** the last connection failure is returned once the send budget or recovery window is exhausted

### Requirement: Claude extra usage presentation
Claude cards and account-list rows SHALL show a warning badge, in existing badge styling, when Anthropic usage data reports extra usage as enabled. The badge SHALL be absent when extra usage is disabled or unreported.

#### Scenario: Extra usage enabled
- **WHEN** the latest usage data reports extra usage enabled for an account
- **THEN** its card and list row show an extra-usage badge explaining that requests beyond subscription limits are billed

### Requirement: Native Claude Message Threads continuity
Native thread continuation SHALL require provenance for the previous message ID
scoped by API key and model and SHALL dispatch only to its originating account.
Thread response message ownership SHALL be persisted before the message ID is
published. The gateway SHALL preserve native history, tool names and cache
markers; it SHALL NOT replay history-less continuations on another account.

#### Scenario: Continuation after soft affinity expiry
- **WHEN** a thread continuation references a retained message and session affinity has expired
- **THEN** the original account serves the request using message provenance

#### Scenario: Missing or foreign thread state
- **WHEN** the previous message has no unexpired provenance in the caller's scope
- **THEN** the gateway returns HTTP 404 with a recognizable thread_not_found marker before upstream dispatch, enabling complete-history replay

#### Scenario: Unavailable thread owner
- **WHEN** the owning account is paused, cooling down, quota-limited or refused the continuation, and the request carries no other account-bound resources
- **THEN** the gateway returns the replayable thread_not_found 404 without dispatching to another account, while recording any owner refusal cooldown

#### Scenario: Unavailable owner with server-tool state
- **WHEN** a thread continuation also references server-tool resources bound to an unavailable owner
- **THEN** the gateway keeps the existing owner-unavailable refusal

#### Scenario: Upstream state expired
- **WHEN** a thread continuation receives an explicit missing-thread upstream 404
- **THEN** the gateway preserves the 404 and publishes the thread_not_found marker without account cooldown or account rotation

#### Scenario: Unrelated not found
- **WHEN** an upstream 404 does not identify missing thread state
- **THEN** it remains an ordinary upstream error

### Requirement: Projected cache TTL ordering
For non-native OAuth instruction projection, the gateway SHALL preserve a valid
caller cache TTL order on the final payload. If relocation places a short
ephemeral marker before a later 1h marker, it SHALL extend that earlier marker
to 1h without downgrading the later marker or removing cache metadata.
Messages and count_tokens SHALL use the same policy. The gateway SHALL NOT
rewrite native caller cache policy or change TTLs to repair an invalid original
order, and SHALL record TTL changes as explicit projection transformations.

#### Scenario: Relocated long-lived instructions
- **WHEN** valid system 1h and user 5m cache controls are reordered by instruction relocation
- **THEN** the earlier projected short cache control becomes 1h and later short controls remain unchanged

#### Scenario: Native cache policy
- **WHEN** native Claude Code sends cache controls
- **THEN** all cache-control metadata remains unchanged

#### Scenario: Invalid original order
- **WHEN** the caller already supplies a 1h marker after a short marker
- **THEN** projection leaves the caller's cache-control values unchanged

### Requirement: Claude tool-choice directive forms
The Claude projection SHALL accept `auto`, `none` and `required` tool-choice
directives in string or single-field object form with identical semantics,
retaining tool declarations. It SHALL send `disable_parallel_tool_use` only with
choices that permit tool use, and SHALL treat only `required` and named-tool
choices as forced when thinking is enabled. Directive objects with additional
fields SHALL be rejected. Native OpenAI passthrough SHALL remain unchanged.

#### Scenario: Object-form none
- **WHEN** a client sends `tool_choice: {"type": "none"}` with declared tools
- **THEN** Claude receives `{"type": "none"}` with the tools still declared

#### Scenario: None without parallel tool use
- **WHEN** a client sends `none` with `parallel_tool_calls: false`
- **THEN** the Claude tool choice carries no parallel-use flag

#### Scenario: Thinking with object-form none
- **WHEN** a client enables reasoning and sends `tool_choice: {"type": "none"}`
- **THEN** the request is projected with thinking enabled

#### Scenario: Malformed directive object
- **WHEN** a directive object carries fields besides `type`
- **THEN** the request fails with an unsupported tool choice error

### Requirement: Refused translated output is not replayed
A translated Claude stream SHALL withhold the first completed tool call and every later event of that response until Claude's stop reason arrives. It SHALL release them for a non-refusal stop and discard them on refusal: a refused turn MUST NOT deliver an executable tool call, and discarded items MUST NOT appear in the terminal output. Sequence numbers delivered to the client SHALL remain contiguous. When a refusal follows items the client already received as done, the gateway SHALL persist a hashed record of the refused response, scoped to the client and independent of model, before the terminal event is delivered. Later translated requests from that client SHALL omit every input item that belongs to a recorded refused response, before replay authentication and continuation projection, and SHALL refresh the record's retention while it is used. Only counts SHALL be logged; refused content, its ids and refusal explanations MUST NOT be stored or logged. A recording failure SHALL fail the stream explicitly.

#### Scenario: Tool call before refusal
- **WHEN** Claude completes a tool call and then stops with refusal
- **THEN** the client receives no done event for the call, the terminal output omits it, and the response fails with invalid_prompt

#### Scenario: Tool turn completes
- **WHEN** Claude completes tool calls and stops with tool_use
- **THEN** the held events are delivered in order before the completed terminal

#### Scenario: Conversation continues after a refusal
- **WHEN** the user continues a conversation after a refusal whose signed thinking the client had already committed
- **THEN** Claude receives the conversation and the new message without the refused reasoning and without a synthetic continuation turn

#### Scenario: Refusal before any committed output
- **WHEN** Claude refuses before any item reached the client as done
- **THEN** no refused-response record is written

#### Scenario: Completed output is unaffected
- **WHEN** a response completes or stops for any other reason
- **THEN** its items are replayed in later requests as before

### Requirement: Positional translated developer messages
Translated Responses developer and system messages that precede every conversation message SHALL form the system prompt with the request instructions. Later developer and system messages SHALL keep their conversation position: each SHALL be placed directly after the next user turn and before the following assistant turn or the end of the messages, never rewriting earlier messages, so later requests reproduce the same prefix. Models whose policy supports mid-conversation system messages SHALL receive them as `system` turns; other models SHALL receive their blocks unchanged between `<system-reminder>` delimiters at the end of that user turn. Requests containing system turns SHALL send the mid-conversation system beta. Signature recovery SHALL ignore system turns when protecting the open tool turn.

#### Scenario: Instruction update before a new prompt
- **WHEN** Codex sends a developer message after an assistant answer followed by the next user message, for a model with mid-conversation system support
- **THEN** Claude receives the developer content as a system turn directly after that user message, and the earlier messages are byte-identical to the previous request

#### Scenario: Update inside a tool loop
- **WHEN** a developer message follows a tool result and precedes the next tool call
- **THEN** the system turn sits between the tool-result user turn and the next assistant turn

#### Scenario: Update between assistant items
- **WHEN** a developer message arrives between two assistant items
- **THEN** it waits for the next user turn and is placed after it

#### Scenario: Model without system turns
- **WHEN** the model's policy lacks mid-conversation system support
- **THEN** the developer content closes the preceding user turn inside `<system-reminder>` delimiters and no system turn is sent

#### Scenario: Recovery behind a system turn
- **WHEN** a signature rejection is recovered for a request ending with a tool result followed by a system turn
- **THEN** the open tool turn keeps its signed thinking

### Requirement: Claude Code-shaped translated tool names
Translated client tools SHALL be sent to Claude under Claude Code-shaped wire names: the Claude Code canonical name when the flat client name has a known mapping, otherwise the PascalCase form of the name. Names starting with `mcp__` and names already in Claude Code form SHALL be kept. Namespaced tools SHALL first be qualified as `namespace__name`. Wire names that collide SHALL be numbered in declaration order, and names that do not satisfy Anthropic's tool-name constraint SHALL be shortened with a stable digest of the qualified name. A request-local table SHALL restore the client's name, namespace and tool kind on every returned call. History tool calls and forced tool choice SHALL use the same wire name as the declaration.

#### Scenario: Known harness tool
- **WHEN** a client declares `terminal` or `read_file`
- **THEN** Claude receives `Bash` or `Read`, and the call it returns reaches the client as `terminal` or `read_file`

#### Scenario: Namespaced tool
- **WHEN** a client declares `spawn_agent` in the `collaboration` namespace
- **THEN** Claude receives `CollaborationSpawnAgent`, and the returned call carries the original name and namespace

#### Scenario: Collision
- **WHEN** two declared tools map to the same wire name
- **THEN** the later one receives a numbered wire name and both resolve to their own client identity

#### Scenario: Replayed history
- **WHEN** history contains a call to a declared tool
- **THEN** the replayed `tool_use` carries the declaration's wire name

### Requirement: Claude catalog models select multi-agent v2
Claude catalog models SHALL advertise `multi_agent_version` `"v2"`, so agent trees rooted on a Claude model use Codex's message-based subagent protocol.

#### Scenario: Claude model in the Codex catalog
- **WHEN** a client lists models and a Claude source model is enabled
- **THEN** its entry carries `multi_agent_version: "v2"`

#### Scenario: Other model sources
- **WHEN** an OpenRouter or OpenAI-compatible source model is listed
- **THEN** its entry carries no `multi_agent_version` from codex-lb

### Requirement: Portable hosted-search history
Hosted-search history that cannot be replayed natively on the destination route SHALL be projected as readable historical assistant text instead of failing. The projection SHALL replace the search call, and any search-state carrier, with one assistant `output_text` message at the call's position. The message SHALL contain the search action — `Web search: <query>`, `Opened page: <url>` or `Found in page <url>: <pattern>` — followed, when result entries are available, by `Sources:` and one `<title> — <url>` line per result. Claude results SHALL supply title and URL from `web_search_result` entries. OpenAI results SHALL supply them from `action.sources` when present.

The rendering SHALL be deterministic for identical history. It MUST NOT include encrypted result content, signatures, provider item identities or page text. It MUST NOT fabricate a search call, encrypted result or server-resource ownership. Retained logical history SHALL keep the original items. Projection diagnostics SHALL count projected searches without content.

The projection SHALL apply to:

- Claude hosted search sent to native OpenAI, in completed and active turns.
- OpenAI `web_search_call` items sent to Claude, in completed and active turns.
- Completed Claude hosted search sent to a different Claude model or account.

#### Scenario: Claude search in a GPT child
- **WHEN** a forked child on native OpenAI replays its Claude parent's completed hosted search
- **THEN** OpenAI receives the query and result titles and URLs as assistant text, and no Claude envelope, `web_search_call` or foreign identity

#### Scenario: OpenAI search in a Claude child
- **WHEN** a Claude request contains an OpenAI `web_search_call` with `action.sources`
- **THEN** Claude receives the query and sources as assistant text, and the request does not fail for missing Claude search state

#### Scenario: OpenAI search without sources
- **WHEN** an OpenAI `web_search_call` has no `action.sources`
- **THEN** Claude receives only the search action line

#### Scenario: Claude search on another Claude model
- **WHEN** completed Claude hosted search belongs to another model or account than the selected route
- **THEN** the selected model receives the projected text and the original call and result blocks are not sent

#### Scenario: Original route
- **WHEN** the conversation later returns to the search's original Claude model and account
- **THEN** the retained call and encrypted result replay natively

### Requirement: Translated assistant messages carry a Responses phase

A translated Claude response SHALL deliver each assistant message with the Responses `phase` that Claude's output
implies. A message SHALL stay open after its text block stops until its phase is known. A following text block SHALL
join the open message as a further `output_text` part, so at most one message is open. Any other valid content block
SHALL close the open message with phase `commentary` before that block's item is added. When Claude stops, the open
message SHALL close with phase `final_answer` for stop reasons `end_turn` and `stop_sequence`, and `commentary` for
`tool_use`. Truncated and paused stops, a refusal whose message was delivered, and streams that end without a stop
reason SHALL close it without a phase. When a stream fails, a message whose text finished SHALL be closed before the
error unless it is withheld behind a tool call. A rejected content block MUST NOT close the open message with a phase.

#### Scenario: answer after work

- **WHEN** Claude streams text, then a tool call, and stops with `tool_use`, and the next response streams text and
  stops with `end_turn`
- **THEN** the first message is done with phase `commentary` before the tool call item is added
- **AND** the second message is done with phase `final_answer`

#### Scenario: consecutive text blocks

- **WHEN** Claude streams two text blocks in a row and stops with `end_turn`
- **THEN** the client receives one message with two `output_text` parts and phase `final_answer`

#### Scenario: incomplete stop

- **WHEN** Claude stops with `max_tokens`, `pause_turn` or `model_context_window_exceeded` after text
- **THEN** the message is done without a phase and the response is incomplete

#### Scenario: failure after text

- **WHEN** a stream fails after a finished text block, because of an upstream error event, a rejected content block or
  a transport failure
- **THEN** the message is done without a phase before the error

### Requirement: Claude reasoning levels from catalog capabilities
When Claude's model catalog reports a model's capabilities, advertised reasoning levels and the thinking mode SHALL be derived from them: adaptive-thinking models SHALL advertise exactly the reported effort levels, including `xhigh` where reported; budget-only models SHALL advertise the documented budget ladder; a model reporting neither SHALL advertise no reasoning. The explicit policy table SHALL apply only when stored catalog entries lack capabilities. The advertised default SHALL be the provider's API default effort for adaptive models (`medium` for Claude Opus 5.5, otherwise `high`) and `medium` for budget models. A requested `xhigh` or `max` the model does not support SHALL be sent as `high`; a requested effort SHALL never be sent as a higher level.

#### Scenario: Opus 5.5 advertises xhigh from the catalog
- **WHEN** the catalog reports adaptive thinking with low, medium, high, xhigh and max effort for Claude Opus 5.5
- **THEN** the Codex model catalog advertises those five levels with default `medium`, and a request for `xhigh` is sent upstream as `xhigh`

#### Scenario: Unsupported xhigh steps down
- **WHEN** a client requests `xhigh` for a model whose catalog reports effort up to `max` without `xhigh`
- **THEN** the request is sent with effort `high`, not `max`

### Requirement: Translated Claude tool IDs are portable

When the service projects Responses tool calls and their outputs into Claude
Messages, it SHALL write each `call_id` as a wire ID matching
`^[a-zA-Z0-9_-]+$`. A call ID already matching that pattern SHALL pass
unchanged unless it starts with the reserved prefix `cxlb_tid_v1_`; every other
call ID SHALL become that prefix followed by the unpadded base64url encoding of
its UTF-8 bytes. A tool call and its result SHALL use the same wire ID, and
distinct call IDs SHALL never share one. Tool-cycle pairing and validation
SHALL use the original call IDs.

#### Scenario: Foreign call ID from another provider

- **GIVEN** history containing a tool call and output with call ID `functions.shell:0`
- **WHEN** the request is projected for Claude
- **THEN** the `tool_use.id` and the `tool_result.tool_use_id` are both
  `cxlb_tid_v1_ZnVuY3Rpb25zLnNoZWxsOjA`

#### Scenario: Claude's own call ID is unchanged

- **GIVEN** history containing a tool call with call ID `toolu_01Abc-d_E`
- **WHEN** the request is projected for Claude
- **THEN** the `tool_use.id` is `toolu_01Abc-d_E`

#### Scenario: Reserved prefix cannot collide

- **GIVEN** history containing a call ID that already starts with `cxlb_tid_v1_`
- **WHEN** the request is projected for Claude
- **THEN** that call ID is encoded and its wire ID differs from every other
  call's wire ID

### Requirement: Relocated OAuth instructions follow the leading user run

When OAuth instruction relocation places the caller's system blocks in a
mid-conversation `system` turn, the service SHALL insert that turn after the
leading run that starts with the first ordinary user turn. User turns and
effort directives (system turns with empty content and an `output_config`)
SHALL continue the run; any other turn SHALL end it. The relocated turn
SHALL therefore precede an assistant turn, another content-bearing system
turn, or the end of `messages`, and no existing message SHALL be rewritten
or reordered.

#### Scenario: Request after client compaction

- **GIVEN** messages consisting of a user summary, an effort directive and a new user message
- **WHEN** instructions are relocated for a model with mid-conversation system support
- **THEN** the relocated system turn is the last message

#### Scenario: Consecutive user turns

- **GIVEN** messages starting with two user turns followed by an assistant turn
- **WHEN** instructions are relocated
- **THEN** the relocated system turn sits between the second user turn and the assistant turn

#### Scenario: Single leading user turn

- **GIVEN** messages starting with one user turn followed by an assistant tool call
- **WHEN** instructions are relocated
- **THEN** the relocated system turn directly follows that user turn, as before

### Requirement: Claude cache misses are attributed to the changed prefix part

The service SHALL remember, for each recent Claude conversation, a digest-only
shape of its latest request: per-tool digests, the system digest, digests of
the other top-level parameters, and per-message digests, all computed with
`cache_control` markers removed. When a request reports no cache read but a
cache write, and a shape exists for the same conversation or, failing that, for
its parent session, the service SHALL log which part differs from that shape:
tools added, removed, changed or reordered, a changed system, changed
parameter names, and the index and block types of the first divergent message.
Requests that read from the cache, and misses without an earlier shape, SHALL
log nothing. Shapes SHALL contain no request content.

#### Scenario: Fork drops a tool

- **GIVEN** a parent session whose latest request declared tools `exec` and `create_canvas`
- **WHEN** a forked conversation from that session sends only `exec` and reports no cache read but a cache write
- **THEN** the service logs the parent as reference and `create_canvas` as removed

#### Scenario: Moved breakpoints are not a divergence

- **GIVEN** a conversation whose next request appends messages and moves its cache breakpoints
- **WHEN** that request reports no cache read but a cache write
- **THEN** the logged tools and system are unchanged and no message diverges

#### Scenario: Cache hit is silent

- **GIVEN** a conversation with a remembered shape
- **WHEN** its next request reports a cache read
- **THEN** the service logs nothing for it
