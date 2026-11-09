## MODIFIED Requirements

### Requirement: Bounded speed work
Exact speed medians SHALL only run for date windows of at most ninety days. Longer windows SHALL retain zero-valued numeric speed fields for compatibility, return `speedMetricsAvailable=false` and the maximum supported speed-window size and SHALL NOT execute median SQL. Every report SHALL include `speedMetricsAvailable` and `speedMetricsMaxDays`. The dashboard SHALL explain the omission using the server's maximum and hide unavailable speed charts.

#### Scenario: Ninety-day report
- **WHEN** an operator requests a 90-day report
- **THEN** the report SHALL include exact daily speed medians
- **AND** `speedMetricsAvailable` SHALL be true

#### Scenario: Longer custom report
- **WHEN** an operator requests a 91-day report
- **THEN** the report SHALL return aggregate totals without running raw median calculations
- **AND** the page SHALL state that speed metrics require a window of ninety days or less
