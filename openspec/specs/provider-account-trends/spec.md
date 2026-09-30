# Provider account trends

## Purpose
Show account-scoped activity and observed quota history using the Codex chart presentation.

## Requirements

### Requirement: Provider-specific chart alignment
Shared charts SHALL align equivalent timestamps. Codex measured quota series SHALL
retain upstream interpolation and monthly labels; other provider series SHALL
retain unknown gaps, and request counts SHALL remain non-percentage values.
#### Scenario: Independent provider observations
- **WHEN** Claude or OpenRouter series lack a sample at another series' timestamp
- **THEN** the missing observation remains unknown rather than interpolated


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

### Requirement: Claude weekly pacing guideline
Future Claude quota observations SHALL persist their reported reset deadline transactionally. Legacy observations SHALL retain unknown deadlines without inferred backfill. A separate Weekly plan chart series SHALL use the native Codex pacing formula: remaining time divided by the seven-day duration, clamped to 0–100 percent. It SHALL begin no earlier than the observation establishing the deadline, stop after expiry or a subsequent unknown deadline, and break across changed reset cycles. The guideline MUST NOT invent future resets or historical deadlines. It SHALL reuse the native dashed-line styling and weekly color and identify itself as an even-consumption guideline distinct from measured quota. Measured hourly series and OpenRouter request-count units SHALL remain unchanged.

#### Scenario: First recorded deadline
- **WHEN** a weekly observation first supplies a reset deadline midway through an hour
- **THEN** the guideline begins at that observation, without filling preceding history

#### Scenario: Unexpected reset or unknown deadline
- **WHEN** a later observation changes or removes the deadline
- **THEN** the old guideline is interrupted and only the new observed cycle may be plotted

#### Scenario: Historical rows without reset deadlines
- **WHEN** existing quota history predates deadline persistence
- **THEN** measured quota remains available but no weekly plan is fabricated for those rows

#### Scenario: Shared chart legend
- **WHEN** a weekly plan exists
- **THEN** the chart and legend use a dashed line in the measured weekly series color without changing OpenRouter charts
