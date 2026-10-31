## MODIFIED Requirements

### Requirement: Lightweight filter options
`GET /api/reports/options` SHALL apply the report date and timezone and return distinct models and nonblank User-Agent
groups within the account and API-key scope, and the provider accounts (`accountId`, `modelSourceId`, `provider`,
`name`) with usage within the API-key scope, without running speed or full-report aggregates. Account options SHALL
NOT be narrowed by the account selection, so selecting an account keeps the others selectable. It SHALL use dashboard
authentication and the same date-range validation as reports.

#### Scenario: Filter catalog loads
- **WHEN** the report page loads or its scope changes
- **THEN** it SHALL request options from the dedicated endpoint instead of a second full report

#### Scenario: Account options ignore the account selection
- **GIVEN** a range with usage on a Codex account and a Claude source
- **WHEN** options are requested with only the Codex account selected
- **THEN** both accounts are listed and the models are limited to the Codex account's usage
