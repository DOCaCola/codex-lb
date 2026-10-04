# Provider account trends

## Purpose
Show account-scoped activity and observed quota history using the Codex chart presentation.

## Requirements

### Requirement: Provider-specific chart alignment
Shared charts SHALL align samples chronologically on a numeric time axis. Codex measured quota series SHALL retain upstream interpolation and monthly labels; other provider series SHALL retain their own observation samples without interpolation, and request counts SHALL remain non-percentage values. Extra timestamps from another series MUST NOT fabricate unknown observations.
#### Scenario: Independent provider observations
- **WHEN** Claude or OpenRouter series lack a sample at another series' timestamp
- **THEN** their own samples remain unchanged, without interpolation or insertion of an artificial gap

### Requirement: Independent trend sample alignment
Trend rendering MUST preserve each series' own samples on a shared chronological axis. Additional guideline timestamps MUST NOT introduce artificial gaps in measured quota or distort time spacing. Explicit unknown hourly observations MUST remain disconnected.

#### Scenario: Mid-hour weekly guideline
- **WHEN** measured quota has consecutive known hourly samples and a guideline sample shares the chart
- **THEN** the measured line remains visible without fabricated unknown points

#### Scenario: Missing hour
- **WHEN** a measured series has an explicitly unknown hour
- **THEN** its line does not connect across that hour

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
Future Claude quota observations SHALL persist their reported reset deadline transactionally. Legacy observations SHALL retain unknown deadlines without inferred backfill. A separate Weekly plan chart series SHALL be produced by the same plan-line computation as the native Codex weekly plan: hourly buckets using each bucket's latest recorded reset deadline, carried forward to later buckets, with remaining time divided by the seven-day duration and clamped to 0–100 percent. It SHALL begin at the first bucket with a known deadline. Deadline changes, including sub-second reporting jitter, MUST NOT interrupt the line; a new reset cycle appears as the line returning toward full remaining capacity. The guideline MUST NOT invent future resets or historical deadlines. It SHALL reuse the native dashed-line styling and weekly color and identify itself as an even-consumption guideline distinct from measured quota. Measured hourly series and OpenRouter request-count units SHALL remain unchanged.

#### Scenario: First recorded deadline
- **WHEN** a weekly observation first supplies a reset deadline
- **THEN** the guideline begins at that observation's hourly bucket, without filling preceding history

#### Scenario: Deadline reporting jitter
- **WHEN** observations report the same reset deadline with sub-second differences
- **THEN** the guideline remains one continuous line

#### Scenario: Unexpected reset or unknown deadline
- **WHEN** a later observation reports a new reset deadline or no deadline
- **THEN** a new deadline applies from that bucket, as on Codex, and a missing deadline keeps the last known one

#### Scenario: Historical rows without reset deadlines
- **WHEN** existing quota history predates deadline persistence
- **THEN** measured quota remains available but no weekly plan is fabricated for those rows

#### Scenario: Shared chart legend
- **WHEN** a weekly plan exists
- **THEN** the chart and legend use a dashed line in the measured weekly series color without changing OpenRouter charts
