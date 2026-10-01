## ADDED Requirements

### Requirement: Claude accounts are listed by name
The Claude account API SHALL return accounts ordered by account name, with the source ID breaking ties.

#### Scenario: Several Claude accounts
- **WHEN** Claude accounts named Zulu, Alpha and Mike exist
- **THEN** the account list returns Alpha, Mike, Zulu
