## ADDED Requirements

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

## MODIFIED Requirements

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
