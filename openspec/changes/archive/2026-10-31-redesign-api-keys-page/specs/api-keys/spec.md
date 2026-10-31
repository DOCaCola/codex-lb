## MODIFIED Requirements

### Requirement: API key edit payload — conditional limits transmission

A key's Settings tab SHALL transmit `limits` in the PATCH payload only when limit values have actually changed. The
system SHALL normalize and compare initial and current limit values to detect changes.

- Metadata-only changes (name, is_active): `limits` field MUST be omitted from the payload
- Identical rule sets with different ordering: MUST be treated as unchanged (`limits` omitted)

Backend contract:
- `limits` absent in payload: limit policy unchanged (usage/reset state preserved)
- `limits` present in payload: policy replacement (state-preserving upsert applied)

#### Scenario: Name-only edit omits limits from payload

- **WHEN** only the API key name is modified on the Settings tab
- **THEN** the PATCH payload does not include the `limits` field

#### Scenario: Reordered identical rules treated as unchanged

- **WHEN** the same limit rules are submitted in a different order
- **THEN** the system treats this as unchanged and omits `limits` from the payload

### Requirement: API-key comparison trend panel

The API Keys page SHALL place a full-width seven-day comparison chart between the header and the keys table, using the existing card and chart styles. It SHALL default to all providers, Cost and Per hour. An accessible provider control SHALL offer All, Codex, Claude, Antigravity and OpenRouter, with provider logos, and SHALL refetch the collection trends for the chosen provider. Accessible controls SHALL switch Cost/Tokens and Per hour/Cumulative without refetching. Hourly mode SHALL use independent, unstacked areas sharing a zero baseline for both costs and tokens; cumulative mode SHALL use independent running-total lines starting from the selected window, with one measurement axis. The five largest series by selected seven-day measure SHALL appear individually; remaining series SHALL be summed as Other without losing usage or coverage. Ties SHALL use stable key identity ordering. Legend controls SHALL hide and restore series. Each key SHALL keep the colour it has in the keys table and rail, independent of mode and provider. Loading, empty, and retryable error states SHALL be explicit. Controls and legend SHALL fit mobile widths. Unknown-only cost points SHALL be gaps rather than apparent free usage, and compact tooltips SHALL distinguish unknown cost from explicit zero-priced requests.

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

#### Scenario: Colours match the table
- **WHEN** a key appears in the chart and in the keys table
- **THEN** its series uses the same colour as its table swatch
