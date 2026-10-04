## MODIFIED Requirements

### Requirement: API key 7-day usage includes account cost breakdown

`GET /api/api-keys/{key_id}/usage-7d` SHALL return `accountCosts[]` in addition to the existing 7-day totals for the selected API key. Each `accountCosts[]` item SHALL include `accountId`, `modelSourceId`, `provider`, `name`, `costUsd`, and `isDeleted`.

The system MUST aggregate `accountCosts[]` from request-log rows whose `api_key_id` matches the selected key and whose `requested_at` falls inside the rolling 7-day window used by the endpoint totals. Rows SHALL be grouped by provider account: the Codex `account_id` or the `model_source_id`. `provider` SHALL be `codex` for Codex accounts, the model-source kind for `claude` and `openrouter` sources, and `null` otherwise. `name` SHALL be the Codex account alias, falling back to its email, or the model-source name.

#### Scenario: Account costs are sorted by descending cost
- **WHEN** a client loads `GET /api/api-keys/{key_id}/usage-7d`
- **AND** multiple grouped account-cost buckets exist in the 7-day window
- **THEN** `accountCosts[]` is ordered by `costUsd` descending

#### Scenario: Provider accounts are attributed by name
- **WHEN** request-log rows in the 7-day window have `account_id = NULL` and a `model_source_id` of an existing Claude source named `Team Claude`
- **THEN** the response includes an `accountCosts[]` item with `modelSourceId` set, `provider: "claude"` and `name: "Team Claude"`

#### Scenario: Codex accounts are labelled by alias
- **WHEN** a Codex account with alias `Alpha` and email `a@example.com` has cost in the window
- **THEN** its `accountCosts[]` item has `provider: "codex"` and `name: "Alpha"`

#### Scenario: Unknown account usage remains separate
- **WHEN** request-log rows in the 7-day window have `account_id = NULL` and `model_source_id = NULL`
- **AND** those rows are not soft-deleted
- **THEN** the response includes an `accountCosts[]` item with `accountId: null`, `modelSourceId: null`, `name: null`, `provider: null`, and `isDeleted: false`

#### Scenario: Deleted account usage is grouped into one bucket
- **WHEN** request-log rows in the 7-day window are marked deleted, or reference a model source that no longer exists
- **THEN** the response groups their cost into a synthetic `accountCosts[]` item with `accountId: null`, `name: null`, and `isDeleted: true`

#### Scenario: Deleted and unknown account usage stay distinct
- **WHEN** the same API key has both deleted-account cost and unknown non-deleted request-log cost inside the 7-day window
- **THEN** the response returns separate `accountCosts[]` items for the deleted and non-deleted buckets

## ADDED Requirements

### Requirement: Account cost legend identifies providers

The API-key cost-by-account legend SHALL show each entry's provider logo, coloured with the entry's slice colour, in place of the colour dot. Entries without a provider SHALL keep the colour dot.

#### Scenario: Provider and fallback markers
- **WHEN** the breakdown contains a Claude entry and an unknown entry
- **THEN** the Claude row shows the Claude logo in its slice colour and the unknown row shows the colour dot
