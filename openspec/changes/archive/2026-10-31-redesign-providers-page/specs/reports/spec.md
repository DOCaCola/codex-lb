## MODIFIED Requirements

### Requirement: Daily account and model splits

`GET /api/reports` MUST return `dailyByAccount` and `dailyByModel` for the filtered range. Each entry MUST carry its
local report `date`, request count, error count, input, cached input, inclusive output and nullable reported reasoning
tokens, the known cost subtotal and its request coverage. `dailyByAccount` entries MUST carry the provider-account
identity (`accountId`, `modelSourceId`, `provider`, `name`) used by `byAccount`; `dailyByModel` entries MUST carry
`model`. For every day, the entries of each split MUST sum to that day's `daily` totals.

#### Scenario: A day served by two accounts and two models
- **GIVEN** a report day with requests on two accounts and two models
- **WHEN** the report is requested
- **THEN** `dailyByAccount` has one entry per account for that day and `dailyByModel` one entry per model
- **AND** each split's requests, tokens and known cost sum to the day's `daily` row

#### Scenario: Errors are counted per account and day
- **GIVEN** a report day on which one account served three requests and one of them failed
- **WHEN** the report is requested
- **THEN** that account's `dailyByAccount` entry for the day has `requests` 3 and `errorCount` 1
