## MODIFIED Requirements

### Requirement: Dashboard weekly credits pace

The dashboard SHALL show weekly quota runway when account weekly capacity credits, remaining credits, reset time, and window length are available. The card MUST present, in priority order: fleet headroom (percent and amount), depletion ETA at the recent burn rate, the next reset relief (arrival time and amount returned), and a survives-to-relief verdict. The response SHALL state its unit: `credits` for Codex and `pro_units` for Claude, and the card SHALL label amounts with that unit. The runway calculation MUST use capacity totals rather than averaging per-account percentages. The dashboard MUST render the card immediately from the overview payload without waiting for any other request, and MAY refine it when the projections payload arrives. Card status MUST derive from the relief verdict (`safe`, `tight`, `runs_dry`) rather than from deviation against a linear schedule. The dashboard projections payload SHALL expose smoothed weekly pace gap fields for display while preserving instantaneous live usage fields.

#### Scenario: Weekly credits pace uses account reset deadlines

- **WHEN** multiple accounts have weekly quota data with different `resetAtSecondary` values
- **THEN** the system computes depletion, relief, and expected remaining weekly credits from each account's own reset time and window length before summing fleet totals

#### Scenario: Weekly credits pace excludes hard-blocked or stale usage rows

- **WHEN** an account is `reauth_required`, paused, deactivated, missing from the account table, or its latest weekly usage sample is older than the freshness window derived from the usage refresh interval
- **THEN** the account is not included in weekly runway totals or forecasts
- **AND** the response reports the excluded stale account count separately from the included account count

#### Scenario: Exhausted accounts still count in weekly credits pace

- **WHEN** an account is `rate_limited` or `quota_exceeded`
- **AND** it has complete, fresh weekly capacity, remaining credits, reset time, and window length
- **THEN** the account is included in weekly runway totals and forecasts

#### Scenario: Current schedule gap is separate from forecast shortfall

- **WHEN** actual remaining weekly credits are lower than scheduled remaining weekly credits
- **THEN** the response reports `scheduleGapCredits` for the current deficit against the linear schedule
- **AND** the response reports `projectedShortfallCredits` only for a future shortfall forecast based on recent burn
- **AND** any surface that presents the linear-schedule deficit describes it as over planned usage, fewer credits remaining than scheduled, or equivalent over-consumption wording rather than "behind schedule"
- **AND** the dashboard labels the two concepts separately

#### Scenario: Displayed pace gap uses configured smoothing

- **GIVEN** the weekly pace gap smoothing window is configured
- **WHEN** recent weekly usage samples are available for the current weekly reset/window segment
- **THEN** the response includes `smoothedDeltaPercent`, `smoothedScheduleGapCredits`, and `paceGapSmoothingMinutes`
- **AND** `actualUsedPercent` remains the live current value
- **AND** the Weekly pace card displays the smoothed gap while keeping `actualUsedPercent` as the live current value

#### Scenario: Weekly pace smoothing resets with quota window

- **GIVEN** a smoothing time window contains samples from before and after a weekly quota reset
- **WHEN** the latest sample belongs to the new reset/window segment
- **THEN** the smoothed pace gap excludes the samples from the previous reset/window segment

#### Scenario: Forecast burn uses recent weekly usage slope

- **WHEN** an account has high cumulative weekly usage from earlier in the window but no recent increase in weekly used percent
- **THEN** the depletion forecast is based on the recent slope and does not assume the earlier full-window average continues

#### Scenario: Near-reset depletion is not a false alarm

- **WHEN** an account has consumed 99% of its weekly quota and 99% of its weekly window has elapsed
- **THEN** the runway verdict treats that account's imminent reset as relief rather than reporting it as over plan

#### Scenario: Missing weekly credit data is omitted

- **WHEN** an account is missing weekly capacity credits, remaining credits, reset time, or window length
- **THEN** that account is omitted from weekly runway calculation

#### Scenario: No valid weekly credit data hides pace

- **WHEN** no account has complete, fresh weekly credits pace data for an `active`, `rate_limited`, or `quota_exceeded` account
- **THEN** the dashboard does not render a fake weekly runway value

#### Scenario: Relief falls back to the full fleet when no account is near exhaustion

- **WHEN** no included account is at or above 95 percent weekly usage
- **THEN** the next relief time is the soonest reset among all included accounts
- **AND** the relief credits sum the used credits of included accounts whose reset falls within one hour of that soonest reset

#### Scenario: Verdict reflects whether relief arrives before depletion

- **WHEN** the depletion ETA at the recent burn rate falls before the soonest reset among accounts at or above 95% weekly usage
- **THEN** the response reports `runwayStatus` as `runs_dry`
- **AND** the card presents the depletion time and the missed relief time together

#### Scenario: Surviving to relief is not an incident

- **WHEN** the depletion ETA falls after the soonest relief reset
- **AND** the margin between them is at least 24 hours and fleet headroom is at least 12 percent
- **THEN** the response reports `runwayStatus` as `safe`
- **AND** the card renders without warning emphasis

#### Scenario: Per-key attribution names the burn source

- **WHEN** request logs exist in the trailing two hours
- **THEN** the weekly pace response no longer carries per-key attribution
- **AND** the adjacent Top consumers card for the same provider names the top API keys so an operator can identify the consumer without leaving the dashboard

#### Scenario: Saturated fleet labels demand as a floor

- **WHEN** every included account is at or above 99.5 percent weekly usage
- **THEN** demand-derived figures are labeled as at-least floors rather than exact demand

#### Scenario: Add-capacity recommendation is stable and gated

- **WHEN** trailing seven-day fleet demand in quota-weeks exceeds current fleet weekly capacity
- **AND** the runway verdict is `runs_dry` or at least one account is saturated
- **THEN** the response recommends additional Pro accounts (Codex) or Pro-equivalents (Claude) computed from the weekly demand surplus
- **AND** the recommendation does not change materially from hour to hour under steady traffic

#### Scenario: Throttle guidance precedes purchase guidance

- **WHEN** the runway verdict is `runs_dry`
- **AND** `throttleToPercent` is available
- **THEN** the card presents throttling to the sustainable rate as the first remedy before any add-capacity suggestion

#### Scenario: Card paints without the projections request

- **WHEN** the overview response has arrived and the projections request is still in flight or failed
- **THEN** the weekly runway card renders its full content from the overview payload with a stable layout footprint

### Requirement: Weekly consumer estimated API costs

The dashboard SHALL show a standalone Top consumers card listing the top API keys by requests and by billable tokens over the trailing two hours, with request count, billable tokens, dominant model and compact USD estimated API cost. The overview and projections payloads SHALL provide the lists per provider (`topConsumers.codex` from native Codex requests and `topConsumers.claude` from Claude requests), and the card SHALL show the list of the selected quota provider. Costs SHALL use recorded request costs across all models and existing coverage rules, never a quota-credit conversion. Unknown, free and incomplete costs SHALL remain distinct, with incomplete details in tooltips. Runway calculations and privacy rules SHALL remain unchanged.

#### Scenario: Provider-scoped consumers
- **WHEN** an API key sent only Claude requests in the trailing two hours
- **THEN** it appears in the Claude list and not in the Codex list

#### Scenario: Multiple models and partial coverage
- **WHEN** a consumer has two priced requests costing $1 and $2 and one unpriced request within the attribution window
- **THEN** its row displays $3.00 with incomplete coverage in the tooltip
- **AND** request counts, tokens and dominant-model selection keep their existing semantics

#### Scenario: Unknown versus free
- **WHEN** one consumer has no known prices and another has explicitly free metered requests
- **THEN** their rows display Unknown and $0.00 respectively

#### Scenario: Responsive presentation
- **WHEN** long consumer names, model names and cost totals are shown at desktop or narrow mobile widths
- **THEN** cost remains readable without causing horizontal page overflow

### Requirement: Dashboard usage donuts present credits as stacked remaining and capacity

The dashboard's primary and secondary usage donuts MUST present remaining amount and capacity as two stacked values separated by a horizontal divider: the remaining count above (bold, `data-testid="donut-center-remaining"`) and the capacity count below (muted, `data-testid="donut-center-capacity"`). Codex values MUST use locale-aware thousands separators (e.g. `7,331` and `7,560`); Claude Pro-unit values MAY show one decimal. Compact-format abbreviation (e.g. `7.33k`) MUST NOT be used in the donut center for these panels.

For Codex the primary donut title MUST read `5-Hour Credits` and the secondary `Weekly Credits`. For Claude they MUST read `5-Hour Quota` and `Weekly Quota`, with a `Pro units` centre caption.

#### Scenario: Dashboard donut shows stacked remaining and capacity

- **WHEN** the dashboard renders a Codex usage donut with `remaining=7331` and `total=7560`
- **THEN** the donut title reads `5-Hour Credits` or `Weekly Credits`
- **AND** the center renders `7,331` in the remaining element and `7,560` in the capacity element
- **AND** a divider separates the two values

## ADDED Requirements

### Requirement: Dashboard quota provider toggle
The dashboard SHALL group the 5-hour ring, weekly ring, weekly pace and Top consumers cards in a Quota section with a Codex | Claude toggle. The toggle SHALL switch all four cards together, persist with the dashboard preferences, and be hidden when no Claude account exists. The cards SHALL lay out in four columns on wide screens, two on medium and one on narrow screens.

#### Scenario: No Claude accounts
- **WHEN** no Claude account is configured
- **THEN** the toggle is not shown and the cards show Codex

### Requirement: Claude quota pooled in Pro units
Claude quota rings and pace SHALL pool accounts in Pro units weighted by plan: Pro 1, Max 5× 5, Max 20× 20, for both windows. Accounts with any other or unknown plan, or without a current observation for the window, SHALL be excluded and listed by name with the reason beneath the rings. The weights SHALL NOT affect routing.

#### Scenario: Mixed plans
- **WHEN** a Pro account is 50% used and a Max 5× account is 20% used in the weekly window
- **THEN** the weekly ring shows 4.5 of 6 Pro units remaining

### Requirement: Dashboard activity below accounts
The global activity statistics (requests, tokens, estimated API cost, conversations, account burn, error rate) SHALL appear below the Accounts section under an Activity heading, independent of the quota provider toggle.

#### Scenario: Toggle does not filter activity
- **WHEN** the quota toggle is switched to Claude
- **THEN** the activity statistics remain fleet-wide
