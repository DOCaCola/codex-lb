## MODIFIED Requirements

### Requirement: Permanent report aggregates
The system SHALL preserve request counts, error and cancellation counts, token totals, cost, first activity, active accounts and distinct normalized conversations in permanent time buckets, including account, model source, API key, model and User-Agent filter dimensions. Report days SHALL respect the requested timezone. Folded history and raw complement SHALL be read in one snapshot without overlap. Partial storage buckets SHALL use raw data; retained history at sub-hour boundaries has the same bounded edge limitation as existing hourly statistics.

#### Scenario: Historical and live data coexist
- **GIVEN** a fold watermark inside the report window
- **WHEN** a filtered report is requested
- **THEN** folded rows and raw rows contribute exactly once and totals match the unfurled raw history

#### Scenario: Retention and lifecycle changes
- **WHEN** retention prunes raw logs
- **THEN** it SHALL wait for report fold coverage and report totals SHALL remain available
- **AND** account soft delete, hard delete and consolidation SHALL mirror report aggregates under the shared fold lock

#### Scenario: Model-source dimension introduction
- **WHEN** the model-source dimension is added to existing report aggregates
- **THEN** retained raw history SHALL be refolded with its model source
- **AND** buckets whose raw rows were already pruned SHALL keep an unattributed model source

## ADDED Requirements

### Requirement: Reports attribute usage to provider accounts
`GET /api/reports` `byAccount` items and active-account counts SHALL use the provider-account identity: the Codex `account_id`, or the `model_source_id` for Claude, OpenRouter and other model sources. Each `byAccount` item SHALL include `accountId`, `modelSourceId`, `provider` and `name` (Codex alias falling back to email, or model-source name).

#### Scenario: Claude usage appears as its own account
- **WHEN** a report window contains Codex usage and usage through a Claude source named `Team Claude`
- **THEN** `byAccount` contains a Codex item and an item with `provider: "claude"` and `name: "Team Claude"`
- **AND** the summary active-account count includes both
