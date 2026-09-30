## MODIFIED Requirements

### Requirement: API-key comparison trend panel

The APIs overview SHALL place a full-width seven-day comparison chart between summary statistics and lifetime breakdown panels, using the existing card and chart styles. It SHALL default to Cost and Per hour. Accessible controls SHALL switch Cost/Tokens and Per hour/Cumulative without refetching. Hourly mode SHALL use independent, unstacked areas sharing a zero baseline for both costs and tokens; cumulative mode SHALL use independent running-total lines starting from the selected window, with one measurement axis. The five largest series by selected seven-day measure SHALL appear individually; remaining series SHALL be summed as Other without losing usage or coverage. Ties SHALL use stable key identity ordering. Legend controls SHALL hide and restore series, and colors SHALL remain stable when modes change. Loading, empty, and retryable error states SHALL be explicit. Controls and legend SHALL fit mobile widths. Unknown-only cost points SHALL be gaps rather than apparent free usage, and compact tooltips SHALL distinguish unknown cost from explicit zero-priced requests.

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
