## MODIFIED Requirements

### Requirement: Dashboard provider cards share one presentation layout

Codex, Claude, Antigravity and OpenRouter dashboard cards SHALL use one card: identity with provider logo, account
colour, plan badge and today's cost, then the account's limits with the weekly window first and one row per window the
account has, then a bottom group pinned to the card's bottom edge. The bottom group SHALL contain the provider footer
and then a status-strip slot. Every Codex card SHALL render its footer with subscription and purchased credits, also
when both are zero, and SHALL show the reset-credit button in that footer whenever reset credits are available,
whether or not the account is limited. The status-strip slot SHALL be reserved on every card and SHALL hold the status
strip only when the account needs attention; the strip's remedy SHALL be Re-auth or Resume. Footer, reset-credit
button and strip therefore sit at the same positions whether or not a card shows a notice. Provider units, unknown or
stale observations, privacy behaviour and action permissions SHALL be preserved without fabricating unsupported
metrics.

#### Scenario: Mixed providers retain their semantics
- **WHEN** Codex, Claude, Antigravity and OpenRouter cards appear together
- **THEN** they share the card layout
- **AND** quota percentages, dollar balances, privacy and actions retain their provider-specific meanings

#### Scenario: Weekly-only account
- **WHEN** an account has only a weekly limit
- **THEN** its card shows no 5h row

#### Scenario: Healthy account has no strip
- **WHEN** an account is active with no notice
- **THEN** its card shows no status strip
- **AND** its status-strip slot stays reserved

#### Scenario: Footer and reset button do not move with a notice
- **WHEN** one Codex card shows a weekly-limit notice and another shows none, and both have reset credits
- **THEN** both show their credits footer and reset-credit button at the same position
- **AND** the weekly-limit strip contains no reset-credit button

#### Scenario: Zero credits still render the footer
- **WHEN** a Codex card has no subscription or purchased credits left
- **THEN** its footer shows `0 + 0 credits`

#### Scenario: Optional email does not shift quotas
- **WHEN** one Codex card has an additional email description and another provider card does not
- **THEN** their limit rows begin at the same vertical position within that row

#### Scenario: Card quotas remain consistent on mobile
- **WHEN** Codex and Claude cards each have two quota windows at a narrow viewport
- **THEN** both render the same limit rows without horizontal document overflow

### Requirement: Dashboard account grid uses intrinsic equal-height cards

Every provider card SHALL use the same grid item. Multi-column account grids SHALL give every card the height of the
tallest card in the grid, across all rows, with limit rows starting at the same position and footers and
status-strip slots at the same positions along the bottom. Single-column layouts SHALL retain natural card heights.
Cards SHALL show their content in full without clipping or inner scrolling and SHALL stay within their column.

#### Scenario: Different provider content stays aligned
- **WHEN** multi-column cards have different amounts of provider content or identity lines
- **THEN** all visible card surfaces have equal heights determined by the tallest content
- **AND** footers and status-strip slots are aligned along the bottom

#### Scenario: Cards in different rows match
- **WHEN** the card grid wraps onto a second row whose cards have fewer limit rows
- **THEN** the second-row cards have the same height as the first-row cards

#### Scenario: Mobile retains full natural content
- **WHEN** the account grid uses a single column
- **THEN** cards use natural content heights and all metrics and actions remain contained and accessible

#### Scenario: Warnings do not shift charts
- **WHEN** one card in a row has a status strip and its neighbour does not
- **THEN** both cards' limit rows start at the same vertical position

### Requirement: Reset actions display a single-unit expiry countdown

Every "Reset" button SHALL display a small countdown label of the soonest-expiring credit's expiry, formatted with the
countdown rule: days only from three days left, days and hours from one day, hours and minutes below one day, minutes
below one hour, and `"now"` for durations under one minute. The label SHALL render in the destructive/red color when
the remaining duration is strictly less than 7 days, and in the default muted color otherwise.

#### Scenario: Days format for duration at or above one day
- **WHEN** a Reset button renders for a credit whose `expires_at` is 12 days away
- **THEN** the countdown label reads `12d`
- **AND** the label uses the default muted color

#### Scenario: Red color under seven days
- **WHEN** a Reset button renders for a credit whose `expires_at` is 6 days away
- **THEN** the countdown label reads `6d`
- **AND** the label uses the destructive/red color

#### Scenario: Hours and minutes use the smaller unit
- **WHEN** a Reset button renders for a credit whose `expires_at` is 13 hours away
- **THEN** the countdown label reads `13h 0m`
- **AND** the label uses the destructive/red color

#### Scenario: Sub-minute duration shows now
- **WHEN** a Reset button renders for a credit whose `expires_at` is 30 seconds away
- **THEN** the countdown label reads `now`
- **AND** the label uses the destructive/red color

## ADDED Requirements

### Requirement: Account notices show the time left

A notice that ends at a known time, such as an exhausted quota window or a subscription end, SHALL carry that time.
The dashboard card strip and the dashboard list row SHALL show the notice headline followed by the time left until it
ends, formatted like the limit-row reset times.

#### Scenario: Exhausted weekly window
- **WHEN** an account's weekly window is exhausted and resets in 2 days 23 hours
- **THEN** its strip shows `Weekly limit · back in 2d 23h`

#### Scenario: Subscription end
- **WHEN** an account's subscription ends in 7 hours
- **THEN** its strip shows `Subscription ends in 7h 0m`

### Requirement: Countdowns coarsen with the time left

Every reset and expiry countdown SHALL round down and show at least one minute. It SHALL show days only from three
days left, days and hours from one day up to three days, hours and minutes below one day, also when the minutes are
zero, and minutes only below one hour. Elapsed durations, such as a conversation's Lasted value, are not countdowns.

#### Scenario: Three days or more
- **WHEN** a quota resets in 6 days 13 hours
- **THEN** its countdown reads `in 6d`

#### Scenario: Between one and three days
- **WHEN** a quota resets in 2 days 23 hours
- **THEN** its countdown reads `in 2d 23h`

#### Scenario: Below one day
- **WHEN** a quota resets in exactly 7 hours
- **THEN** its countdown reads `in 7h 0m`

#### Scenario: Below one hour
- **WHEN** a quota resets in 42 minutes
- **THEN** its countdown reads `in 42m`

### Requirement: OpenRouter amounts use the dashboard currency format

Dashboard dollar amounts, including OpenRouter balances, allowances and daily spend, SHALL use the en-US currency
format. OpenRouter balances MAY show up to four fraction digits.

#### Scenario: OpenRouter amounts match other providers
- **WHEN** an OpenRouter card shows a daily spend of 0 and a balance of 5.7394
- **THEN** they render as `$0.00` and `$5.7394`
