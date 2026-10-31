## ADDED Requirements

### Requirement: Antigravity metadata retry after failure
A failed account, catalog or quota metadata check SHALL retain the last successful
observation and set the endpoint's next attempt time: the reported retry delay for
a 429, otherwise the endpoint's refresh interval. Scheduled checks SHALL wait for
that time. A manual check SHALL wait only when the time comes from a 429 rate
limit and SHALL otherwise run immediately.

#### Scenario: Manual check after a local failure
- **WHEN** a metadata reply failed to parse and the operator checks limits before the retry time
- **THEN** the check reaches Google immediately

#### Scenario: Manual check while rate limited
- **WHEN** Google answered 429 with a retry delay
- **THEN** manual and scheduled checks send nothing until that time
