## MODIFIED Requirements

### Requirement: Provider-specific chart alignment
Shared charts SHALL align samples chronologically on a numeric time axis. Codex measured quota series SHALL retain upstream interpolation and monthly labels; other provider series SHALL retain their own observation samples without interpolation, and request counts SHALL remain non-percentage values. Extra timestamps from another series MUST NOT fabricate unknown observations.

#### Scenario: Independent provider observations
- **WHEN** Claude or OpenRouter series lack a sample at another series' timestamp
- **THEN** their own samples remain unchanged, without interpolation or insertion of an artificial gap

## ADDED Requirements

### Requirement: Independent trend sample alignment
Trend rendering MUST preserve each series' own samples on a shared chronological axis. Additional guideline timestamps MUST NOT introduce artificial gaps in measured quota or distort time spacing. Explicit unknown hourly observations and changed-reset guideline gaps MUST remain disconnected.

#### Scenario: Mid-hour weekly guideline
- **WHEN** measured quota has consecutive known hourly samples and the guideline starts mid-hour
- **THEN** the measured line remains visible without fabricated unknown points

#### Scenario: Missing hour
- **WHEN** a measured series has an explicitly unknown hour
- **THEN** its line does not connect across that hour
