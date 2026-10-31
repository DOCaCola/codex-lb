## ADDED Requirements

### Requirement: Reports toolbar

The `/reports` page MUST start with one toolbar card and MUST NOT render a page title or subtitle. The first row MUST
contain the `7d`, `30d`, `90d` and `Custom` range presets, the selected range as a readable label, the comparison
window, the time the report was generated and a refresh action. Start and end date inputs MUST be shown while
`Custom` is active. The second row MUST contain multi-select `Accounts`, `API keys`, `Models` and `User agents`
filters, a `Reset` action shown while any filter is active, and a `Sections` menu.

#### Scenario: Toolbar replaces title and filter card
- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page shows the toolbar card without a page title
- **AND** the default `7d` preset is highlighted and its range and comparison window are shown

#### Scenario: Custom range shows date inputs
- **WHEN** the operator activates `Custom`
- **THEN** start and end date inputs are shown with the current range

#### Scenario: Refresh refetches the report
- **WHEN** the operator activates refresh
- **THEN** the report and options queries refetch and the generation time updates

### Requirement: Reports daily trend

The `/reports` page MUST render one `Daily trend` card with metric tabs `Cost`, `Input tokens`, `Output tokens` and
`Requests`, and split tabs `Total`, `Account` and `Model` defaulting to `Account`. Values MUST be drawn as stacked
daily bars for every day of the selected range. The `Account` and `Model` splits MUST show the five largest series by
the selected metric and sum the remainder as `Other`; account series MUST use the account chart colours and provider
logos in the legend. The `Total` split MUST divide input tokens into uncached and cached input and output tokens into
visible output and reported reasoning. The tooltip MUST show full values.

#### Scenario: Cost split by account
- **GIVEN** a report with cost on six accounts
- **WHEN** the trend shows `Cost` split by `Account`
- **THEN** each day stacks the five largest accounts and `Other`
- **AND** each day's stack sums to that day's known cost

#### Scenario: Input tokens total split
- **WHEN** the trend shows `Input tokens` with the `Total` split
- **THEN** each bar stacks uncached input and cached input

#### Scenario: Empty report
- **GIVEN** the report has no daily rows
- **THEN** the trend shows a no-data state instead of zero bars

### Requirement: Reports breakdown lists

The `/reports` page MUST render `Accounts`, `Models` and `User agents` breakdown cards as bar lists that show every
row without an inner scroll area, with a shared `Cost` / `Requests` switch defaulting to `Cost`. Each row MUST show its
value and share; shares MUST be computed from the known subtotals of the listed rows, and the cost view MUST show an
incomplete-coverage marker when the report coverage is incomplete. Account rows MUST show the provider logo in the
account chart colour. Activating a row MUST toggle that row in the matching filter.

#### Scenario: Every model is visible
- **GIVEN** a report with nine models
- **WHEN** the breakdown renders
- **THEN** all nine model rows are visible without scrolling inside the card

#### Scenario: Row toggles a filter
- **WHEN** the operator activates the row of a model
- **THEN** that model is added to the `Models` filter and the report refetches
- **AND** activating it again removes it from the filter

### Requirement: Reports latency and throughput charts

The `/reports` page MUST render TTFT, TPS and queue-wait medians as three compact charts with straight segments through
the real daily points and the median of the window as the headline. A value that exceeds four times the median of the
other days MUST be drawn at the top edge with its value label instead of setting the scale.

#### Scenario: Outlier does not set the scale
- **GIVEN** daily TPS medians around 80 and one day at 2,941
- **WHEN** the TPS chart renders
- **THEN** the scale follows the other days and the outlier is drawn at the top edge labelled `2,941`

### Requirement: Reports routing diagnostics are collapsible

Thread identity and cache locality MUST be shown in a `Routing diagnostics` card that is collapsed by default. Its
header MUST show accounts per conversation, the switch rate and the cache hit rate once loaded. The thread-identity
request MUST be sent only while the card is open and its section is visible.

#### Scenario: Diagnostics load on demand
- **WHEN** `/reports` opens
- **THEN** no thread-identity request is sent
- **WHEN** the operator expands `Routing diagnostics`
- **THEN** the thread-identity request is sent and the tiles and disclosure note render

### Requirement: Reports sections menu

The `Sections` menu MUST let the operator show or hide the `trend`, `breakdown`, `perf`, `table` and `diagnostics`
sections. The toolbar and summary cards MUST always be visible.

#### Scenario: Hiding a section
- **WHEN** the operator unchecks `Latency & throughput` in the `Sections` menu
- **THEN** the latency and throughput charts are not rendered and the other sections remain

### Requirement: Reports daily breakdown shows the full calendar window

The `/reports` daily breakdown table SHALL render one row per calendar day in the selected date range without an inner
scroll area. Day labels SHALL follow the dashboard date display preference: the localized short weekday, day and month
by default, and the ISO `yyyy-mm-dd` date when the ISO preference is selected. If the reports API omits one or more
days inside that range, the table SHALL synthesize zero-valued rows for those days using the same row styling as
API-backed rows.

#### Scenario: Daily breakdown fills missing days with zero-valued rows

- **WHEN** the selected reports window spans `2026-06-05` through `2026-06-12`
- **AND** the reports API returns daily rows for every day except `2026-06-06`
- **THEN** the daily breakdown renders a row for `2026-06-06`
- **AND** that row shows zero requests, zero input tokens, zero output tokens, zero cost, and zero accounts
- **AND** that row uses the same row styling as neighboring rows

#### Scenario: Daily breakdown shows every day

- **WHEN** the daily breakdown contains thirty rows
- **THEN** every row is rendered in the page flow without scrolling inside the table

#### Scenario: Daily breakdown follows the ISO preference

- **GIVEN** the ISO date display preference is selected
- **WHEN** the reports API returns a daily bucket row with `date` set to `2026-06-01`
- **THEN** the daily breakdown table renders that row label as `2026-06-01`

### Requirement: Reports custom range prevents, explains, and recovers from inverted dates

The `/reports` start-date input MUST use the earlier of the browser-local current day and a present end date as its
native `max`, and the end-date input MUST use a present start date as its native `min` while retaining the
browser-local current day as its `max`. If both values are present and the start date is later than the end date, both
controls MUST expose `aria-invalid`, both MUST reference the same localized inline corrective message through an
accessible description, and neither the filtered Reports query nor the Reports filter-options query MAY send a request.
Correcting either bound so the range is ordered MUST clear the invalid state and resume each distinct Reports query
with the corrected bounds.

#### Scenario: Reciprocal native bounds prevent routine inverted selection

- **GIVEN** `/reports` has a selected start date and end date
- **THEN** the start-date control's `max` is the earlier of the end date and the browser-local current day
- **AND** the end-date control's `min` is the start date
- **AND** the end-date control's `max` remains the browser-local current day

#### Scenario: Bypassed inverted input is accessible and sends no Reports request

- **WHEN** typed, restored, or programmatically supplied Reports dates have a start date later than the end date
- **THEN** both date controls expose `aria-invalid`
- **AND** both controls reference one visible localized message that tells the operator to place the start date on or
  before the end date
- **AND** no `GET /api/reports` or `GET /api/reports/options` request is sent

#### Scenario: Retry while inverted only retries API keys

- **GIVEN** `/reports` has an inverted date range and loading API-key options failed
- **WHEN** the operator activates the page-level Retry action
- **THEN** the API-key options query sends a retry request
- **AND** neither Reports query sends a request

#### Scenario: Correcting either invalid bound resumes Reports queries

- **GIVEN** `/reports` has an inverted date range and both Reports queries are disabled
- **WHEN** the operator corrects either date bound so the start date is on or before the end date
- **THEN** both controls clear the invalid state and accessible description
- **AND** the corrective message is removed
- **AND** each distinct Reports query sends one request using the corrected ordered bounds

## MODIFIED Requirements

### Requirement: Reports page renders English user-facing labels

The dashboard SHALL render `/reports` with the following exact page-owned user-facing labels for the current reports
surface:

- `Loading...`
- `Cost`
- `Tokens`
- `Requests`
- `Active conversations`
- `Errors`
- `Daily trend`
- `Breakdown`
- `Latency & throughput`
- `Daily breakdown`
- `Routing diagnostics`
- `Day`
- `Input`
- `Output`
- `Accounts`
- `Total`
- `Failed to load report data:`
- `Failed to load filter options:`
- `Some report data could not be loaded. Try reloading.`
- `Retry`

Backend-provided strings, account values, model values, and raw server error payload text SHALL remain out of scope
for this wording change unless `/reports` renders page-owned labels around them.

#### Scenario: Reports page shows English labels

- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page renders no `Cost Report` title
- **AND** the summary cards include `Cost`, `Tokens`, `Requests`, `Active conversations` and `Errors`
- **AND** the section titles include `Daily trend`, `Breakdown`, `Latency & throughput`, `Daily breakdown` and
  `Routing diagnostics`
- **AND** the daily table headings include `Day`, `Input`, `Output`, `Cost` and `Accounts`

#### Scenario: Reports page state labels are English

- **WHEN** `/reports` renders a loading, empty, or error state
- **THEN** the loading label is `Loading...`
- **AND** page-owned error wrappers use `Failed to load report data:` and `Failed to load filter options:` when those
  failures render
- **AND** the retry warning is `Some report data could not be loaded. Try reloading.`
- **AND** the retry button label is `Retry`

### Requirement: Reports page exposes visible filter controls

The `/reports` page SHALL expose visible filter controls for `7d`, `30d` and `90d` quick presets, a `Custom` range
with start and end dates, and multi-select `Accounts`, `API keys`, `Models` and `User agents` filters. When an
authenticated operator clicks one of the quick presets, the page SHALL visibly highlight that preset. When the
operator edits the start date or end date of the custom range, the page SHALL highlight `Custom` until another quick
preset is clicked. The start and end date inputs SHALL disallow selecting dates later than the browser's current local
calendar date. Account options SHALL come from `GET /api/reports/options` and include Codex accounts and provider
accounts; a selected Codex account SHALL be sent as `account_id` and a selected provider account as `model_source_id`.

#### Scenario: Reports page shows report filter controls

- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page exposes the `7d`, `30d`, `90d` and `Custom` presets and the `Accounts`, `API keys`, `Models`
  and `User agents` filters

#### Scenario: Quick preset highlight follows the selected preset

- **WHEN** an authenticated operator clicks the `30d` quick preset on `/reports`
- **THEN** the page visibly highlights the `30d` preset
- **AND** the page updates the start and end dates to the `30d` preset range

#### Scenario: Quick preset highlight clears after manual date edits

- **WHEN** an authenticated operator edits the start date or end date of the custom range
- **THEN** the page highlights `Custom`
- **AND** the page keeps the edited date range values

#### Scenario: Report date inputs disallow future dates

- **WHEN** an authenticated operator shows the custom range on `/reports`
- **THEN** the start date and end date inputs prevent selecting a date later than the browser's current local calendar
  date

#### Scenario: Provider account selection

- **WHEN** the operator selects a Codex account and a Claude account
- **THEN** the report request contains `account_id` for the Codex account and `model_source_id` for the Claude account

### Requirement: Reports safely persists visibility

Reports MUST store the visible section IDs as a JSON array under the exact localStorage key
`codex-lb-reports-visible-sections`. The only known section IDs MUST be the following five, in this canonical order:
`trend`, `breakdown`, `perf`, `table`, `diagnostics`. This canonical order MUST be used for normalization,
persistence, and rendering. Missing storage MUST default to all five known section IDs. A valid array MUST be filtered
to known IDs, deduplicated, and normalized to canonical order; an empty array MUST remain empty. Malformed JSON,
non-array values, arrays containing any non-string values, and localStorage access failures MUST default to all five
known section IDs. Storage failures MUST NOT disable current-session in-memory visibility changes.

#### Scenario: Reports restores a persisted subset

- **GIVEN** localStorage contains a valid JSON array with the IDs `trend` and `table`
- **WHEN** the `/reports` page initializes
- **THEN** the daily trend and daily breakdown sections render
- **AND** the other three sections do not render

#### Scenario: Reports ignores unknown IDs and normalizes persisted values

- **GIVEN** localStorage contains a valid JSON array with known IDs in a non-canonical order, duplicate known IDs, and
  unknown IDs
- **WHEN** the `/reports` page initializes
- **THEN** unknown IDs are ignored
- **AND** duplicate IDs occur only once
- **AND** the selected IDs are normalized to canonical order

### Requirement: Visibility does not narrow data fetching

Changing section visibility MUST NOT change Reports filter values, the report TanStack Query key, request parameters,
response schema, or response parsing. Reports MUST continue requesting the complete `GET /api/reports` payload and MUST
NOT send a section-specific API parameter. Hiding the `diagnostics` section MUST stop the thread-identity request,
which belongs to that section only.

#### Scenario: Visibility changes leave the report query unchanged

- **GIVEN** Reports has loaded the complete `GET /api/reports` payload
- **WHEN** the operator changes the visible sections
- **THEN** the Reports filter values remain unchanged
- **AND** the report TanStack Query key and request parameters remain unchanged
- **AND** the complete report payload remains requested and parsed using the existing response schema

### Requirement: Reports API is accessible through the dashboard route map

The dashboard surface SHALL expose a reports page at route `/reports` and route to data loaded from `GET /api/reports`
with date-range, account, provider-account, API-key, model and user-agent filters.

#### Scenario: Dashboard reports page uses `/api/reports`
- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page loads the aggregated reports payload from `GET /api/reports`
- **AND** allows filtering by date range, account, API key, model and user agent
- **AND** uses the returned payload to render summary cards, the daily trend, breakdown lists, latency charts and the
  daily breakdown

### Requirement: Reports page exposes a visible user-agent filter

The dashboard SHALL render `/reports` with a visible multi-select `User agents` filter beside the `Models` filter. Its
choices SHALL use normalized `request_logs.useragent_group` values, and each selected value SHALL be sent as a repeated
`useragent_group` parameter on `GET /api/reports` requests.

#### Scenario: Reports page shows the user-agent filter
- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page exposes a visible `User agents` filter beside `Models`

#### Scenario: Reports page requests filtered data by normalized user-agent group
- **WHEN** an authenticated operator selects two `User agents` values on `/reports`
- **THEN** the page refetches `GET /api/reports` with one `useragent_group` parameter per selected value

#### Scenario: Reports page reuses the relaxed reports query for user-agent filter choices
- **WHEN** `/reports` loads or refreshes filter choices
- **THEN** the page obtains `Models` and `User agents` options from `GET /api/reports/options` scoped by dates,
  timezone, accounts and API keys
- **AND** the options query does not change when only model or User-Agent selection changes

#### Scenario: Reports page shows one shared relaxed-catalog error for report filter choices
- **WHEN** the `GET /api/reports/options` query fails
- **THEN** the page shows one page-owned `Failed to load filter options:` error

### Requirement: Reports user-agent distribution preserves unknown buckets without collisions

`GET /api/reports` SHALL aggregate request-log rows whose normalized `request_logs.useragent_group` is `null` into a
`byUseragent` bucket labeled `Missing User-Agent`. Real normalized `request_logs.useragent_group = "Unknown"` rows
SHALL remain in a separate `Unknown` bucket. When `/reports` or `GET /api/reports` is filtered with
`useragent_group=Missing User-Agent`, the system SHALL match those same null-backed rows, while
`useragent_group=Unknown` SHALL match only real `"Unknown"` rows. The `/reports` `User agents` breakdown SHALL render
the `Missing User-Agent` row with a fixed gray marker and bar instead of a rotated palette color.

#### Scenario: Reports payload includes missing and real Unknown user-agent traffic

- **WHEN** `GET /api/reports` aggregates request logs that include one or more rows with
  `request_logs.useragent_group = null`
- **AND** one or more rows with normalized `request_logs.useragent_group = "Unknown"`
- **THEN** the response `byUseragent` array includes an entry with `useragent: "Missing User-Agent"`
- **AND** that entry aggregates only the null-backed rows' request counts and costs
- **AND** the response separately includes an entry with `useragent: "Unknown"` for the real normalized `"Unknown"`
  rows

#### Scenario: Reports filters distinguish missing and real Unknown user-agent traffic

- **WHEN** `/reports` or `GET /api/reports` requests `useragent_group=Missing User-Agent`
- **THEN** the returned report aggregates include only rows whose normalized `request_logs.useragent_group` is `null`
- **WHEN** `/reports` or `GET /api/reports` requests `useragent_group=Unknown`
- **THEN** the returned report aggregates include only rows whose normalized `request_logs.useragent_group` is the real
  string `"Unknown"`

#### Scenario: Reports page renders the missing user-agent bucket with fixed gray styling

- **WHEN** the `User agents` breakdown renders data that includes `useragent: "Missing User-Agent"`
- **THEN** the `Missing User-Agent` marker and bar use a fixed gray color

### Requirement: Reports daily charts fill missing selected days with zero-value rows

The dashboard SHALL render the `/reports` daily trend from a continuous daily series covering every selected day from
the current `startDate` through `endDate`. When `GET /api/reports` omits a selected date, the page SHALL insert a
zero-value daily row for that date before rendering the trend.

#### Scenario: Missing API dates render as zero-value chart points

- **WHEN** an authenticated operator views `/reports` for a selected date range and the `daily` response omits one or
  more selected dates
- **THEN** the daily trend includes a bar slot for every selected day from `startDate` through `endDate`
- **AND** each omitted date renders with zero cost, tokens and requests

### Requirement: Daily Breakdown supports explicit visible-column sorting

The dashboard SHALL render the `/reports` `Daily breakdown` with sortable columns for `Day`, `Requests`,
`Conversations`, `Input`, `Output`, `Reasoning`, `Cost`, `Errors`, `Cancelled`, `Accounts`, `TTFT` and `TPS`. The
default sort SHALL be `Day` descending. A totals row SHALL follow the day rows and SHALL NOT take part in sorting.

#### Scenario: Daily Breakdown defaults to newest day first

- **WHEN** an authenticated operator opens `/reports`
- **THEN** the `Daily breakdown` rows are ordered by `Day` descending by default

#### Scenario: Daily Breakdown toggles sorting for a visible column

- **WHEN** an authenticated operator activates any `Daily breakdown` column header
- **THEN** the table sorts by that column
- **AND** activating the same header again toggles the sort direction between ascending and descending
- **AND** the totals row stays last

### Requirement: Reports Tokens summary subtitle shows cached totals

The dashboard SHALL render the `/reports` `Tokens` summary-card detail line as the cached share of input tokens
followed by the output-token total, and SHALL show input, cached input, output and reported reasoning totals in the
card's tooltip.

#### Scenario: Tokens subtitle includes cached total

- **WHEN** an authenticated operator opens `/reports`
- **THEN** the `Tokens` summary card shows the cached input share and the output total
- **AND** its tooltip lists input, cached, output and reasoning totals

### Requirement: Daily Breakdown shows cached input tokens inline

The dashboard SHALL render `/reports` `Daily breakdown` `Input` cells as the input-token total followed by the cached
share of that day's input in muted secondary text.

#### Scenario: Input Tokens cell shows cached input token count

- **WHEN** a `Daily breakdown` row has 1,000 input tokens of which 900 are cached
- **THEN** the `Input` cell renders the formatted input total followed by `90% cached`

#### Scenario: Input Tokens cell shows zero cached tokens explicitly

- **WHEN** a `Daily breakdown` row has input tokens and `cachedInputTokens = 0`
- **THEN** the `Input` cell renders the formatted input total followed by `0% cached`
- **AND** if `inputTokens = 0` the cell renders `0` without a cached share

### Requirement: Reports summary cards show previous-window deltas conservatively

`GET /api/reports` SHALL expose a `comparison` block for the `Cost`, `Tokens`, and `Requests` summary cards that
includes `canCompare` plus the previous-window totals for cost, tokens, and requests. The current window and previous
window SHALL use equal calendar-window lengths derived from the selected report date range. The endpoint SHALL set
`canCompare` to `true` only when eligible report history fully covers the immediately preceding window. When
`canCompare` is `false`, the `/reports` summary cards SHALL hide the previous-window percentage indicators. Even when
`canCompare` is `true`, an individual summary card SHALL hide its own percentage indicator when that card's
previous-window total is zero. Indicators SHALL use a neutral muted color with a direction arrow; an increase or
decrease SHALL NOT be colored as good or bad.

#### Scenario: Reports summary cards show previous-window increase

- **WHEN** `GET /api/reports` returns current summary totals plus `comparison.canCompare: true`
- **AND** a previous-window total for `Cost`, `Tokens`, or `Requests` is lower than the current total for that same
  card
- **THEN** the matching summary card renders a neutral upward percentage-change indicator

#### Scenario: Incomplete previous window suppresses comparison

- **WHEN** the earliest eligible report activity is later than the start of the immediately preceding report window
- **THEN** `GET /api/reports` returns `comparison.canCompare: false`
- **AND** the `/reports` summary cards do not render previous-window percentage indicators

#### Scenario: Zero previous total suppresses the matching card indicator

- **WHEN** `GET /api/reports` returns `comparison.canCompare: true`
- **AND** the previous-window total for one of `Cost`, `Tokens`, or `Requests` is `0`
- **THEN** that summary card does not render a previous-window percentage indicator
- **AND** the other summary cards may still render percentage indicators when their own previous-window totals are
  greater than `0`

### Requirement: Reports line charts show no-data when daily rows are absent

When the Reports daily trend or a latency chart receives an empty daily-row array, it SHALL render a no-data empty
state and SHALL NOT render a continuous zero-filled series for the selected date range. When the daily-row array has
at least one row, the trend MAY still fill missing days with zeros.

#### Scenario: Empty daily payload hides the zero-line chart

- **GIVEN** `GET /api/reports` returns no daily rows
- **WHEN** the daily trend or a latency chart renders
- **THEN** it shows a no-data empty state
- **AND** it does not render bars or lines of zero values

#### Scenario: Partial daily payload still fills missing days

- **GIVEN** the daily trend receives daily rows for some days in the selected range
- **WHEN** the trend renders
- **THEN** missing days in that range are still filled with zero values

### Requirement: Reports full-value USD displays use grouped currency formatting

The dashboard SHALL render non-compact USD Cost values on `/reports` through the shared currency formatter so values at
or above one thousand include locale-appropriate grouping separators and exactly two fractional digits. This
requirement applies to the Cost summary value, its average-per-day detail, Daily breakdown Cost cells, breakdown row
values, and daily trend tooltip values. Trend axis ticks MAY use compact notation.

#### Scenario: Summary and daily Cost values exceed one thousand USD

- **WHEN** an authenticated operator views `/reports` data whose full-value Cost amount is `1400`
- **THEN** the Cost summary value renders `$1,400.00`
- **AND** a Daily breakdown Cost cell whose amount is `1400` renders `$1,400.00`
- **AND** a breakdown row whose cost is `1400` renders `$1,400.00`
- **AND** a daily trend tooltip whose amount is `1400` renders `$1,400.00`

#### Scenario: Intentionally compact Cost visualization remains compact

- **WHEN** the daily trend renders a Cost axis tick of `1400`
- **THEN** the tick may render a compact label such as `$1.4K`
- **AND** the full-value Cost displays remain grouped currency values

## REMOVED Requirements

### Requirement: Reports distribution donuts show compact active-metric totals

**Reason**: The model and user-agent donuts are replaced by breakdown bar lists that show full values and shares.

**Migration**: Use the `Breakdown` section; its `Cost` / `Requests` switch replaces the donut metric toggle.

### Requirement: Reports distribution donuts show active-metric totals

**Reason**: The donuts and their four-row scrolling legends hid rows and are removed.

**Migration**: Use the `Models` and `User agents` breakdown lists, which show every row.

### Requirement: Reports exposes a persisted line-chart visibility filter

**Reason**: The five per-metric line charts are replaced by one daily trend and three latency charts.

**Migration**: Use the `Sections` menu; visibility is stored per section under `codex-lb-reports-visible-sections`.
The previous `codex-lb-reports-visible-charts` preference is not migrated.

### Requirement: Reports page renders a user-agent distribution card

**Reason**: The user-agent donut card is replaced by the `User agents` breakdown list.

**Migration**: Use the `User agents` card in the `Breakdown` section.

### Requirement: Reports distribution cards toggle between cost and requests

**Reason**: The distribution cards are removed.

**Migration**: The `Breakdown` section has one `Cost` / `Requests` switch for its three lists.

### Requirement: Reports daily charts use symmetric horizontal padding

**Reason**: The `Cost by Day` and `Tokens by Day` charts are removed.

**Migration**: The daily trend card replaces both charts.

### Requirement: Reports daily breakdown renders a continuous calendar window

**Reason**: The table no longer scrolls inside a seven-row box, which cut off a day and the last column, and day labels
follow the date display preference instead of always being ISO.

**Migration**: Replaced by "Reports daily breakdown shows the full calendar window".

### Requirement: Reports date controls prevent, explain, and recover from inverted ranges

**Reason**: Account options now come from the Reports filter-options query, so a retry while the range is inverted can
no longer retry a separate Accounts query.

**Migration**: Replaced by "Reports custom range prevents, explains, and recovers from inverted dates".
