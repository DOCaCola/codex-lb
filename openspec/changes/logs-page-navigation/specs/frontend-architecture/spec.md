## ADDED Requirements

### Requirement: Logs page keeps navigation in view

The Logs page SHALL render no page title. It SHALL render one toolbar card holding the view switch, the active view's
time range, refresh, a one-line summary and a compact pager (range, previous and next); in the Request Logs view the
toolbar's second row SHALL hold the search, filters, conversation badge, reset and column controls. The summary SHALL
show the filtered request count with its short cost, the full cost coverage on hover, or the conversation count.

Each view's table SHALL render in a pane that fills the remaining viewport height and scrolls its rows inside, with a
pinned column header and the full pager in its footer, so the page height does not change with page size, paging or
live arrivals. Changing the page or the query SHALL return the pane to its first row. The pagers SHALL be hidden only
while the first page is empty.

Request-log cells SHALL be at most two lines high: secondary model, transport and token details share one truncated
line, and error details show the error code and a truncated message on one line with the full message on hover and in
request details.

On the first page, live arrivals SHALL appear in place while the pane is scrolled to the top. While it is scrolled
down, inserted rows SHALL NOT move the rows in view, and a button SHALL count the arrivals and return to the top;
the count SHALL clear once the pane is back at the top.

#### Scenario: Pager stays in view on a long page

- **GIVEN** 100 request-log rows on a page
- **WHEN** the Logs page renders
- **THEN** the toolbar pager and the pane footer pager are visible without scrolling the page

#### Scenario: Paging returns to the first row

- **GIVEN** the reader has scrolled the request-log pane down
- **WHEN** they move to the next page or change a filter
- **THEN** the pane shows the new page from its first row
- **AND** the page itself does not scroll

#### Scenario: Arrivals do not move a scrolled reader

- **GIVEN** the first request-log page is scrolled down
- **WHEN** a refresh inserts two new requests at the top
- **THEN** the rows in view stay in place
- **AND** a "2 new requests" button is shown
- **WHEN** the reader activates it or scrolls back to the top
- **THEN** the pane is at the top and the button is gone

### Requirement: Conversation filter badge is removable and summarized in the toolbar

When a conversation filter is active, the request-log filters MUST render a removable conversation badge between the
Statuses control and Reset. Dismissing the badge MUST clear only the conversation filter and reset pagination. The
filtered requests' count and cost MUST be summarized by the Logs toolbar summary, which uses the response's `total`
and `costCoverage`; the page MUST NOT render a separate conversation summary.

#### Scenario: Dismissing the badge clears only conversation state
- **GIVEN** the conversation badge and other request-log filters are active
- **WHEN** the badge is dismissed
- **THEN** only the conversation filter is cleared
- **AND** pagination resets
- **AND** the other filters remain active

#### Scenario: Toolbar summarizes the filtered conversation
- **GIVEN** the active conversation filter matches 12 requests with a known cost of `$1.23`
- **WHEN** the request-log page renders
- **THEN** the toolbar summary reads `12 requests · $1.23`
- **AND** no separate conversation summary is rendered

## REMOVED Requirements

### Requirement: Conversation filter state is removable and summarized

**Reason**: The separate conversation summary sentence is replaced by the Logs toolbar summary.

**Migration**: Covered by "Conversation filter badge is removable and summarized in the toolbar".
