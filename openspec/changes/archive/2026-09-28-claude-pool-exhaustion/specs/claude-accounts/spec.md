## ADDED Requirements

### Requirement: Claude pool exhaustion diagnostics
Selection SHALL distinguish quota-only exhaustion from other unavailability within the authorized model/owner scope. Quota-only exhaustion SHALL return429; mixed or unknown unavailability SHALL retain503. Known candidate recovery SHALL account for every applicable temporary barrier, using the latest deadline per candidate and earliest across fully known candidates. Unknown deadlines MUST NOT be fabricated. Hard owner errors SHALL retain their code and scope. HTTP errors SHALL include a ceil-rounded positive Retry-After when justified. Actual exhausted upstream errors and local admission contracts SHALL remain unchanged.

#### Scenario: Multiple restrictions
- **WHEN** one candidate has quota reset in two hours and model cooldown in five, and another recovers in three
- **THEN** the reported known recovery delay is three hours

#### Scenario: Known exhaustion without a deadline
- **WHEN** all candidates are quota-exhausted but no candidate has a complete recovery deadline
- **THEN** the response remains429 without a fabricated Retry-After
