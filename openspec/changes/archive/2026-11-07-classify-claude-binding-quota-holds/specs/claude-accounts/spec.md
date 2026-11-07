## ADDED Requirements

### Requirement: Binding Claude cooldown classification
For an otherwise eligible account, quota SHALL determine the refusal when its known admission horizon exceeds every transient cooldown. A tie or unknown quota horizon with an active transient hold SHALL remain transient. Credential and refresh exclusions SHALL retain precedence. Evidence MUST remain intact. The pool SHALL report usage exhaustion only when every candidate is quota-blocked.

#### Scenario: Short throttle overlaps exhausted quota
- **WHEN** a model throttle ends at 12:22 and five-hour quota admission resumes at 12:40
- **THEN** Responses HTTP and WebSocket refusals report 429 usage_limit_reached with the observed reset
- **AND** native Messages uses rate_limit_error and no upstream request is dispatched

#### Scenario: Transient candidate remains
- **WHEN** a transient hold equals or exceeds the quota horizon, or a pool sibling is transiently blocked
- **THEN** the refusal remains retryable

### Requirement: Claude quota resets require window evidence
Quota resets SHALL derive from observed blocking-window reset times independently of Retry-After. Every blocking quota window must have a known future reset to report an account reset. Every quota-blocked candidate must have a known reset to report the earliest pool reset. Admission cooldowns MUST NOT fabricate reset timestamps. Non-quota refusals SHALL omit quota-reset fields.

#### Scenario: Retry deadline differs from reset
- **WHEN** a named quota cooldown outlasts its observed window reset
- **THEN** Retry-After reflects admission and resets_at reflects only the observed window reset

#### Scenario: Unknown reset
- **WHEN** any relevant quota reset is unknown
- **THEN** resets_at and resets_in_seconds are omitted

## MODIFIED Requirements

### Requirement: Claude pool exhaustion diagnostics
Selection SHALL apply binding-hold classification within the authorized model and owner scope. Quota-only refusal SHALL return 429 usage_limit_reached for Responses and rate_limit_error for native Messages, without plan_type. Other exclusions retain their terminal or retryable contract. Retry-After SHALL reflect admission recovery; reset fields require observed quota evidence. HTTP and WebSocket SHALL preserve status, ownership, blocking windows and timing without exposing account identities.

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
- **WHEN** the required owner is refreshing or its binding hold is an unknown cooldown
- **THEN** the owner error remains503 without becoming a quota-only refusal

#### Scenario: Terminal continuation owner
- **WHEN** the required owner is paused or requires reauthentication
- **THEN** the owner error is400 invalid_request_error without becoming a quota-only refusal

#### Scenario: WebSocket quota refusal
- **WHEN** a downstream Responses WebSocket turn has a quota-only owner exclusion
- **THEN** its error frame carries status429, usage_limit_reached, the owner code and available reset fields and retry-after header without leaking credentials
