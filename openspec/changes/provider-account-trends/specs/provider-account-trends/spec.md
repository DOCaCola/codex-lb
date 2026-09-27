## ADDED Requirements

### Requirement: OpenRouter activity history
OpenRouter account details SHALL display hourly request counts for the past seven
days, scoped to that account's model source. The chart SHALL describe codex-lb
recorded activity and SHALL NOT display quota resets or quota percentages.
Deleted request logs MUST be excluded; empty hours within the retained period
SHALL have zero requests. Unknown accounts SHALL return not found.

#### Scenario: Separate accounts
- **WHEN** requests are recorded for two OpenRouter accounts
- **THEN** each chart includes only its own recorded requests

### Requirement: Claude quota history
Successful Claude usage refreshes SHALL persist observed quota windows atomically
with the refreshed state. Failed refreshes MUST NOT produce observations.
History older than thirty days SHALL be pruned on successful account refresh;
charts SHALL display the past seven
days as hourly average remaining percentages, with missing hours represented as gaps.
Account deletion SHALL remove quota history. Historical data MUST NOT be fabricated.

#### Scenario: Missing observations
- **WHEN** no valid quota observation exists in an hour
- **THEN** its chart value is missing rather than zero or carried-forward quota

### Requirement: Shared chart presentation
Provider trend charts SHALL reuse the native Codex account chart rendering and
layout conventions with provider-appropriate labels, units, loading, error and
empty states. Claude SHALL support its five-hour, weekly and model-specific weekly windows.

#### Scenario: OpenRouter units
- **WHEN** activity is plotted
- **THEN** the axis and tooltip show request counts with no percentage formatting
