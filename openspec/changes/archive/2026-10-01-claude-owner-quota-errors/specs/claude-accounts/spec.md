## MODIFIED Requirements

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
