## ADDED Requirements

### Requirement: API-key collection seven-day trends

The system SHALL serve `GET /api/api-keys/trends` and its trailing-slash equivalent under the existing API-key dashboard read permission. The response SHALL contain `since`, `until`, and `series`, with each series carrying `keyId`, `name`, `isDeleted`, and hourly `cost` and `tokens` points on a common rolling seven-day UTC grid. Costs SHALL preserve priced, unpriced, unmetered, and unknown-coverage metadata. Tokens SHALL use input plus output, or reasoning tokens when output is absent, matching individual key trends. Warmup and unauthenticated usage SHALL be excluded. Retained usage for deleted keys SHALL appear in one anonymous deleted-keys series. Keys without requests in the window SHALL be omitted. Folded history and raw requests SHALL be counted exactly once, including partial boundary hours.

#### Scenario: Compare two keys on the same timeline
- **WHEN** two API keys have requests inside the seven-day window
- **THEN** their series use identical hourly timestamps and preserve their individual costs and token totals
- **AND** requests outside the window and warmups do not contribute

#### Scenario: Preserve deleted usage and incomplete pricing
- **WHEN** a deleted key has retained usage and a current key has unpriced requests
- **THEN** deleted usage appears separately without its former name
- **AND** the current key's cost points report incomplete coverage

#### Scenario: Protect collection trends
- **WHEN** a principal lacks API-key read permission
- **THEN** both collection trend URL forms reject access under the existing dashboard authorization contract

### Requirement: API-key comparison trend panel

The APIs overview SHALL place a full-width seven-day comparison chart between summary statistics and lifetime breakdown panels, using the existing card and chart styles. It SHALL default to Cost and Per hour. Accessible controls SHALL switch Cost/Tokens and Per hour/Cumulative without refetching. Hourly mode SHALL use stacked areas; cumulative mode SHALL use independent running-total lines starting from the selected window, with one measurement axis. The five largest series by selected seven-day measure SHALL appear individually; remaining series SHALL be summed as Other without losing usage or coverage. Ties SHALL use stable key identity ordering. Legend controls SHALL hide and restore series, and colors SHALL remain stable when modes change. Loading, empty, and retryable error states SHALL be explicit. Controls and legend SHALL fit mobile widths. Unknown-only cost points SHALL be gaps rather than apparent free usage, and compact tooltips SHALL distinguish unknown cost from explicit zero-priced requests.

#### Scenario: Switch measure and accumulation
- **WHEN** the user selects Tokens and Cumulative
- **THEN** each line represents that key's running input-plus-output token total within the seven-day window
- **AND** switching back to Per hour restores the individual hourly values

#### Scenario: Many keys preserve totals
- **WHEN** more than five series have usage
- **THEN** the five largest selected-measure series are shown individually and the remaining series are combined as Other
- **AND** the combined totals and cost coverage equal all returned series

#### Scenario: Hide and restore a series on mobile
- **WHEN** the user toggles a legend item at a narrow viewport
- **THEN** its series hides and restores without resetting the other controls or causing horizontal page overflow
