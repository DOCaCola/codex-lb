## ADDED Requirements

### Requirement: Terminal Claude availability errors
When at least one exclusion exists and every exclusion in the authorized model and required-owner scope is paused,
credentials, model or reasoning, selection SHALL return HTTP or WebSocket status
400 with invalid_request_error and its existing pool or owner code. Such an error
SHALL contain routing diagnostics but no Retry-After or reset fields. It MUST NOT
use client authentication status 401 or change the selected provider. The existing
reasoning-only error code SHALL remain unchanged.

Any temporary, unknown or per-attempt excluded candidate SHALL prevent terminal
classification. Mixed or unknown unavailability SHALL remain 503; quota-only
exhaustion SHALL remain 429. Token expiry with refreshable credentials SHALL remain
eligible for dispatch-time refresh. Required-owner scope SHALL never expand to
another account as a consequence of terminal classification.

#### Scenario: Previous model requires reauthentication
- **WHEN** a compact request names a Claude model and every authorized account requires reauthentication
- **THEN** it receives status 400 invalid_request_error with claude_pool_unavailable without upstream dispatch
- **AND** the gateway does not change the request model or conversation history

#### Scenario: Permanently unavailable owner
- **WHEN** a continuation requires an account with non-ready credentials while another account is eligible
- **THEN** it receives status 400 with previous_response_owner_unavailable without dispatch to the other account

#### Scenario: Temporary alternative remains
- **WHEN** one scoped account requires reauthentication and another is refreshing or quota-exhausted
- **THEN** the pool error remains retryable 503 under the existing mixed-pool contract

#### Scenario: Equivalent ingress paths
- **WHEN** a permanently unavailable pool is requested through Responses HTTP, Responses WebSocket, Messages or token counting
- **THEN** each surface preserves status 400 and the terminal error code and type

## MODIFIED Requirements

### Requirement: Claude pool exhaustion diagnostics
Selection SHALL distinguish quota-only exhaustion from other unavailability within the authorized model/owner scope. Quota-only exhaustion SHALL return429, including a required continuation owner; permanent exclusions SHALL follow the terminal availability contract; temporary mixed or unknown unavailability SHALL retain503. Known candidate recovery SHALL account for every applicable temporary barrier, using the latest deadline per candidate and earliest across fully known candidates. Unknown deadlines MUST NOT be fabricated. Hard owner errors SHALL retain their code and scope. Quota refusals SHALL identify observed blocking windows without exposing account identities or history. HTTP errors SHALL include a ceil-rounded positive Retry-After when justified. Known recovery SHALL include resets_at as integer Unix seconds rounded up and resets_in_seconds in public error details; downstream Responses WebSocket errors SHALL preserve those details, status and safe Retry-After. Quota-only refusals SHALL use error type `usage_limit_reached` on OpenAI-envelope surfaces, which Codex presents as a usage limit with its reset time, and `rate_limit_error` on native Anthropic Messages surfaces. They MUST NOT carry `plan_type`. Actual exhausted upstream errors and local admission contracts SHALL remain unchanged.

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
- **WHEN** the required owner is refreshing or blocked by unknown cooldown evidence
- **THEN** the owner error remains503 without becoming a quota-only refusal

#### Scenario: Terminal continuation owner
- **WHEN** the required owner is paused or requires reauthentication
- **THEN** the owner error is400 invalid_request_error without becoming a quota-only refusal

#### Scenario: WebSocket quota refusal
- **WHEN** a downstream Responses WebSocket turn has a quota-only owner exclusion
- **THEN** its error frame carries status429, usage_limit_reached, the owner code and available reset fields and retry-after header without leaking credentials
