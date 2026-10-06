## ADDED Requirements

### Requirement: Claude quota observation provenance
Each persisted Claude quota observation SHALL record whether it came from the usage API or from inference response headers. Consecutive-observation deduplication SHALL compare only observations of the same provenance. Quota pacing and demand calculations SHALL use a single provenance so that systematic disagreement between the two sources is not counted as consumption. Legacy observations without provenance SHALL NOT be assigned one retroactively.

#### Scenario: Interleaved sources
- **WHEN** usage-API observations report 41% and inference-header observations report 40% for the same window, alternating
- **THEN** both are stored with their provenance
- **AND** weekly demand computed from usage-API observations does not count the alternation as consumption
