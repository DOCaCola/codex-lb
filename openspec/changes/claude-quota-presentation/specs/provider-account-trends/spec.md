## ADDED Requirements

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
