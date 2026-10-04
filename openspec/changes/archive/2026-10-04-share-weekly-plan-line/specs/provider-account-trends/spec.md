## MODIFIED Requirements

### Requirement: Independent trend sample alignment
Trend rendering MUST preserve each series' own samples on a shared chronological axis. Additional guideline timestamps MUST NOT introduce artificial gaps in measured quota or distort time spacing. Explicit unknown hourly observations MUST remain disconnected.

#### Scenario: Mid-hour weekly guideline
- **WHEN** measured quota has consecutive known hourly samples and a guideline sample shares the chart
- **THEN** the measured line remains visible without fabricated unknown points

#### Scenario: Missing hour
- **WHEN** a measured series has an explicitly unknown hour
- **THEN** its line does not connect across that hour

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
