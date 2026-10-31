## ADDED Requirements

### Requirement: Speed medians read the report range once

The speed-median aggregation for `GET /api/reports` MUST read request logs in a single pass that is bounded by
constant `requested_at` limits equal to the start of the report's first day and the end of its last day. The TTFT,
TPS and queue medians MUST be derived from that one set of samples.

#### Scenario: Medians use bounded request-log reads

- **GIVEN** a report range of seven days or fewer
- **WHEN** `GET /api/reports` computes speed medians
- **THEN** the statement constrains `requested_at` to the report range with constant bounds
- **AND** request logs outside the range are not read
- **AND** the TTFT, TPS and queue medians per day equal those of the individual samples in that day
