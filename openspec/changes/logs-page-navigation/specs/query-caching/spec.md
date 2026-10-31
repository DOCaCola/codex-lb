## ADDED Requirements

### Requirement: Conversation-filtered totals are pagination-independent

When `conversation_id` is present, the request-log response's `total` and `costCoverage` MUST be computed together
from the complete active filter set, independent of page limit and offset, and MUST NOT mix a cached count with a
fresh cost. `costCoverage.knownCostUsd` MUST sum stored `cost_usd` values, with no matches represented as zero. The
response MUST NOT carry a separate `conversation` block.

#### Scenario: Aggregates ignore pagination
- **GIVEN** a filtered conversation has twelve matching requests across multiple
  pages with a total stored cost of `1.23`
- **WHEN** page one and a later page are requested with different limit or
  offset values
- **THEN** both responses report `total` as `12`
- **AND** both responses report `costCoverage.knownCostUsd` as `1.23`

#### Scenario: No matching rows return zero aggregates
- **GIVEN** a conversation filter and active filters match no request logs
- **WHEN** the request-log listing is requested
- **THEN** the response reports `total` as `0`
- **AND** the response reports `costCoverage.knownCostUsd` as `0`

## REMOVED Requirements

### Requirement: Filtered responses expose pagination-independent conversation aggregates

**Reason**: The `conversation` block duplicated `total` and `costCoverage` and its only consumer was removed.

**Migration**: Covered by "Conversation-filtered totals are pagination-independent".
