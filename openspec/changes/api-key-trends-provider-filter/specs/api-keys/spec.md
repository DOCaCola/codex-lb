## MODIFIED Requirements

### Requirement: API-key collection seven-day trends

The system SHALL serve `GET /api/api-keys/trends` and its trailing-slash equivalent under the existing API-key dashboard read permission. The response SHALL contain `since`, `until`, and `series`, with each series carrying `keyId`, `name`, `isDeleted`, and hourly `cost` and `tokens` points on a common rolling seven-day UTC grid. Costs SHALL preserve priced, unpriced, unmetered, and unknown-coverage metadata. Tokens SHALL use input plus output, or reasoning tokens when output is absent, matching individual key trends. Warmup and unauthenticated usage SHALL be excluded. Retained usage for deleted keys SHALL appear in one anonymous deleted-keys series. Keys without requests in the window SHALL be omitted. Folded history and raw requests SHALL be counted exactly once, including partial boundary hours. An optional `provider` query parameter (`codex`, `claude`, `openrouter` or `openai_compatible`) SHALL restrict every series to usage served by that provider: Codex is usage without a model-source kind (or the subscription kind), every other provider is the model-source kind recorded on the request. Folded hourly history SHALL retain that kind as a dimension so filtering is exact for folded and raw hours alike; history folded before the dimension existed SHALL be re-folded from retained raw requests. Any other `provider` value SHALL be rejected with 422.

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

#### Scenario: Filter trends by provider
- **WHEN** one key has Codex, Claude and OpenRouter usage in both folded and raw hours
- **AND** the collection trends are requested with `provider=claude`
- **THEN** the key's series contains only its Claude usage from both folded and raw hours
- **AND** requesting without `provider` returns the combined usage of all providers

### Requirement: API-key comparison trend panel

The APIs overview SHALL place a full-width seven-day comparison chart between summary statistics and lifetime breakdown panels, using the existing card and chart styles. It SHALL default to all providers, Cost and Per hour. An accessible provider control SHALL offer All, Codex, Claude and OpenRouter, with provider logos, and SHALL refetch the collection trends for the chosen provider. Accessible controls SHALL switch Cost/Tokens and Per hour/Cumulative without refetching. Hourly mode SHALL use independent, unstacked areas sharing a zero baseline for both costs and tokens; cumulative mode SHALL use independent running-total lines starting from the selected window, with one measurement axis. The five largest series by selected seven-day measure SHALL appear individually; remaining series SHALL be summed as Other without losing usage or coverage. Ties SHALL use stable key identity ordering. Legend controls SHALL hide and restore series, and colors SHALL remain stable when modes change. Loading, empty, and retryable error states SHALL be explicit. Controls and legend SHALL fit mobile widths. Unknown-only cost points SHALL be gaps rather than apparent free usage, and compact tooltips SHALL distinguish unknown cost from explicit zero-priced requests.

#### Scenario: Compare hourly values independently
- **WHEN** two keys have hourly costs of 2 and 3 or hourly token counts of 200 and 300
- **THEN** each area's height represents its own value from zero, not a stacked sum
- **AND** hiding one series does not change the remaining series' measurements

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

#### Scenario: Filter the chart by provider
- **WHEN** the user selects Claude in the provider control
- **THEN** the chart shows each key's Claude usage only, keeping the selected measure, accumulation and legend choices
- **AND** selecting All restores the combined usage
