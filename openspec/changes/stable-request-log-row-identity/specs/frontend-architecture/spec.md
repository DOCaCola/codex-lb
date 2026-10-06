## MODIFIED Requirements

### Requirement: Dashboard request log highlights live arrivals

The dashboard request log SHALL give each row that first appears through a refresh of an unchanged query context (filters, search, timeframe, conversation, page size and page) on the first page a tinted background that fades to the normal row background over a few seconds. Arrival SHALL be determined by log-row identity, so a request that completes after newer requests started is highlighted wherever it is placed, and separate rows sharing a request ID (such as a refused attempt and its retry) are tracked and rendered independently in server order. The initial load, any query-context change and placeholder data shown while a new context loads SHALL establish a new baseline without highlighting. Later pages SHALL NOT highlight rows. Refreshes that only change other dashboard data SHALL NOT interrupt a fade in progress.

#### Scenario: Refresh adds a request
- **WHEN** the first page refreshes and contains a log row that was not on the previous page of the same context
- **THEN** that row starts with a tinted background that fades to the normal background
- **AND** rows that were already shown are not highlighted

#### Scenario: Context change does not highlight
- **WHEN** the operator changes a filter, the search, the page size or the page
- **THEN** no row of the newly loaded result is highlighted

#### Scenario: Later pages do not highlight
- **WHEN** the operator views a page after the first and a refresh shifts new entries onto it
- **THEN** no row is highlighted

#### Scenario: Retried rows share a request ID
- **WHEN** two log rows share a request ID and a refresh prepends a newer row and drops an older one
- **THEN** the table shows exactly the returned rows in server order with no leftover rows
