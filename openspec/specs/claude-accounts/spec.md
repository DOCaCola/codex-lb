# Claude Accounts

## Purpose

Provide separately owned Claude OAuth credentials and faithful native and adapted inference without an intermediate gateway.

## Requirements

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

#### Scenario: Native signed history outlives ownership retention
- **WHEN** native account-bound history is submitted after its one-hour ownership retention expires
- **THEN** it fails explicitly and requires portable context rather than selecting a different account

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
