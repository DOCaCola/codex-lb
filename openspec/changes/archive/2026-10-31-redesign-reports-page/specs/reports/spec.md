## ADDED Requirements

### Requirement: Multi-value model and user-agent filters

`GET /api/reports` MUST accept the `model` and `useragent_group` query parameters zero or more times each. Repeated
values of one parameter MUST match rows with any of those values, and different parameters MUST combine with AND.
`useragent_group=Missing User-Agent` MUST continue to match rows without a User-Agent group. The same filters MUST
apply to the summary, comparison, daily rows, daily splits, breakdowns and speed medians, and MUST be part of the
report cache key independent of their order.

#### Scenario: Two models are selected
- **WHEN** `GET /api/reports` is requested with `model=gpt-a&model=gpt-b`
- **THEN** every report aggregate includes rows for `gpt-a` or `gpt-b` and no other model

#### Scenario: Missing and named user agents are combined
- **WHEN** `GET /api/reports` is requested with `useragent_group=Missing User-Agent&useragent_group=CLI`
- **THEN** the aggregates include rows without a User-Agent group and rows in the `CLI` group

### Requirement: Provider-account filter

`GET /api/reports` and `GET /api/reports/options` MUST accept `model_source_id` zero or more times alongside
`account_id`. When either is present a row MUST match if its `account_id` is among the selected account IDs or its
`model_source_id` is among the selected model-source IDs, so Codex accounts and Claude, OpenRouter and other provider
accounts can be selected together.

#### Scenario: A Codex account and a Claude account are selected
- **WHEN** a report is requested with `account_id=codex-1&model_source_id=claude-1`
- **THEN** the aggregates include usage of `codex-1` and usage served through `claude-1`, and no other account

### Requirement: Daily account and model splits

`GET /api/reports` MUST return `dailyByAccount` and `dailyByModel` for the filtered range. Each entry MUST carry its
local report `date`, request count, input, cached input, inclusive output and nullable reported reasoning tokens, the
known cost subtotal and its request coverage. `dailyByAccount` entries MUST carry the provider-account identity
(`accountId`, `modelSourceId`, `provider`, `name`) used by `byAccount`; `dailyByModel` entries MUST carry `model`.
For every day, the entries of each split MUST sum to that day's `daily` totals.

#### Scenario: A day served by two accounts and two models
- **GIVEN** a report day with requests on two accounts and two models
- **WHEN** the report is requested
- **THEN** `dailyByAccount` has one entry per account for that day and `dailyByModel` one entry per model
- **AND** each split's requests, tokens and known cost sum to the day's `daily` row

### Requirement: Known-cost report averages

`summary.avgCostPerDay` MUST be the known cost subtotal divided by the inclusive local calendar window for every
report, including reports with unpriced, unmetered or unverified requests. The summary coverage fields MUST continue to
identify an incomplete subtotal. Model and user-agent entries MUST NOT carry a `percentage` field; clients derive
shares from the entries' known subtotals and coverage.

#### Scenario: Average under incomplete coverage
- **GIVEN** a seven-day report with a known cost of 70 and one unpriced request
- **WHEN** the report is requested
- **THEN** `summary.avgCostPerDay` is 10 and `summary.unpricedRequests` is 1
