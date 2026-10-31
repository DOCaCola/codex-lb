## ADDED Requirements

### Requirement: Dashboard header summarises account health

The dashboard header SHALL show the page title, one line of account health and a refresh button, without a
subtitle. The line SHALL state how many of all accounts can take work and, when present, which accounts are limited
and when the first of them comes back, how many are paused, how many need sign-in, and when the next 5-hour window
resets. Names SHALL follow privacy blurring.

#### Scenario: Limited account comes back later
- **WHEN** five of six accounts are active and one is limited until 14:30
- **THEN** the line reads that five of six accounts can take work and names the limited account with its return time

### Requirement: Dashboard remaining quota card

The quota section SHALL offer a Codex, Claude or Antigravity switch when accounts of more than one of those
providers exist. For Codex and Claude, a Remaining credits (Codex) or Remaining quota (Claude, in Pro units) card SHALL
show a 5-hour and a weekly ring with remaining of capacity and the percent left, a table of each account's remaining
5-hour and weekly amount with reset countdowns, and a total row. Accounts excluded from pooling SHALL be marked and
explained in a note. Antigravity SHALL show remaining quota per model family. Ring values SHALL use compact numbers.

#### Scenario: Codex remaining credits
- **WHEN** Codex accounts have 2,850 of 2,850 five-hour and 61,360 of 95,760 weekly credits left
- **THEN** the rings show 2.85K of 2.85K and 61.36K of 95.76K with 100% and 64% left
- **AND** the table lists each account and the totals

### Requirement: Top consumers show recent cost activity

The overview and projections payloads SHALL give each top consumer `costBuckets`: twelve known-cost sums of
ten-minute buckets covering the two-hour attribution window, oldest first. The Top consumers card SHALL draw them as a
sparkline in the key's colour.

#### Scenario: Cost in the latest bucket
- **WHEN** a key's only request in the window cost $0.125 and was made in the last ten minutes
- **THEN** its `costBuckets` are eleven zeros followed by 0.125

### Requirement: Dashboard activity strip

Below the accounts, the dashboard SHALL show requests, tokens, estimated API cost, account burn and error rate as one
strip of compact metrics with sparklines, with the 1d / 7d / 30d overview timeframe switch beside its header. Account
burn SHALL show the weekly account-equivalent value with the 5-hour value as meta.

#### Scenario: Switch timeframe
- **WHEN** an operator selects 30d beside the Activity header
- **THEN** the strip shows the 30-day metrics

### Requirement: Dashboard accounts header counts account states

The dashboard `Accounts` header SHALL show a hint derived from all provider accounts: the total count and the
ready count, followed by the limited, paused and need-sign-in counts when they are not zero. Ready SHALL mean a
normalized status of `active`; limited SHALL include `limited` and `exceeded`; need sign-in SHALL include `reauth`
and `deactivated`.

#### Scenario: Mixed account states
- **WHEN** accounts have statuses `active`, `paused` and `rate_limited`
- **THEN** the hint reads `3 accounts · 1 ready · 1 limited · 1 paused`

### Requirement: Dashboard accounts offer card and list views

The Dashboard Accounts section SHALL allow operators to choose between cards and a compact list. The default mode
SHALL remain cards and the selection SHALL persist locally. The list SHALL show the same accounts in the same order
with account identity and provider, status with notice and remedy, two limit meters with percent and reset countdown,
and today's cost.

#### Scenario: Dashboard defaults to card view
- **WHEN** the account view-mode preference is unset
- **THEN** the Dashboard Accounts section renders account cards

#### Scenario: Operator switches to list view
- **WHEN** an operator selects list mode
- **THEN** the cards are replaced by a list of the same accounts with status, limit meters and today's cost

#### Scenario: Account view mode persists locally
- **WHEN** an operator selects list mode
- **AND** later returns to the dashboard in the same browser profile
- **THEN** the Dashboard Accounts section renders in list mode

### Requirement: Codex dashboard cards show subscription and purchased credits

Account summary responses SHALL expose nullable upstream purchased-credit metadata as `creditsHas`,
`creditsUnlimited`, and `creditsBalance`, alongside calculated remaining subscription credits for each available
quota window. The Codex card footer MUST present remaining subscription credits and purchased credits as two values,
subscription first, and MUST NOT use one as a fallback replacement for the other. When `creditsUnlimited` is true,
the purchased value SHALL render `Unlimited`. The subscription value SHALL select remaining credits with the
following precedence: monthly credits for monthly-only accounts; secondary credits for weekly-only accounts;
otherwise secondary credits when available, falling back to primary credits.

#### Scenario: Zero purchased balance does not hide subscription quota
- **WHEN** an account summary has `creditsBalance = 0.0`
- **AND** `remainingCreditsSecondary = 35910.0`
- **THEN** the card footer shows `35,910 + 0 credits`

#### Scenario: Unlimited applies only to purchased credits
- **WHEN** an account summary has `creditsUnlimited = true`
- **THEN** the purchased value shows `Unlimited`
- **AND** the subscription value still shows its own remaining quota

## MODIFIED Requirements

### Requirement: Dashboard provider cards share one presentation layout

Codex, Claude, Antigravity and OpenRouter dashboard cards SHALL use one card: identity with provider logo, account
colour, plan badge and today's cost, then the account's limits with the weekly window first and one row per window the
account has, then a status strip with its remedy (Re-auth, Resume, Reset credit) only when the account needs
attention, then a footer only when it carries information. Codex footers SHALL show subscription and purchased
credits and the reset-credit button. Provider units, unknown or stale observations, privacy behaviour and action
permissions SHALL be preserved without fabricating unsupported metrics.

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

#### Scenario: Optional email does not shift quotas
- **WHEN** one Codex card has an additional email description and another provider card does not
- **THEN** their limit rows begin at the same vertical position within that row

#### Scenario: Card quotas remain consistent on mobile
- **WHEN** Codex and Claude cards each have two quota windows at a narrow viewport
- **THEN** both render the same limit rows without horizontal document overflow

### Requirement: Dashboard account grid uses intrinsic equal-height cards

Every provider card SHALL use the same grid item. Multi-column account grids SHALL give cards in a row equal heights,
with limit rows starting at the same position and status strips and footers aligned along the bottom. Single-column
layouts SHALL retain natural card heights. Cards SHALL show their content in full without clipping or inner scrolling
and SHALL stay within their column.

#### Scenario: Different provider content stays aligned
- **WHEN** multi-column cards have different amounts of provider content or identity lines
- **THEN** all visible card surfaces in a row have equal heights determined by the tallest content
- **AND** status strips and footers in the same row are aligned along the bottom

#### Scenario: Mobile retains full natural content
- **WHEN** the account grid uses a single column
- **THEN** cards use natural content heights and all metrics and actions remain contained and accessible

#### Scenario: Warnings do not shift charts
- **WHEN** one card in a row has a status strip and its neighbour does not
- **THEN** both cards' limit rows start at the same vertical position

### Requirement: Dashboard limit warm-up controls

The dashboard SHALL expose global limit warm-up controls in Settings and per-account opt-in/status in the account
settings on the Providers page. Dashboard account cards and list rows SHALL NOT show limit warm-up state or controls.
The global default SHALL be disabled. Settings SHALL include an exhausted-threshold percent control that determines
which pre-reset usage samples count as exhausted for reset-confirmed warm-up.

#### Scenario: Configure warm-up behavior
- **WHEN** an operator opens Settings
- **THEN** the dashboard shows controls for enabling limit warm-up, selecting primary/secondary/both windows, setting
  the warm-up model, setting the prompt, setting the exhausted threshold, and setting the cooldown

#### Scenario: Validate warm-up settings before save
- **WHEN** an operator edits warm-up model, prompt, exhausted threshold, or cooldown fields
- **THEN** the dashboard enforces the same non-empty, max-length, percent, and integer cooldown bounds as the backend
  API before enabling save

#### Scenario: Show per-account opt-in and last attempt
- **WHEN** an operator opens a Codex account's settings on the Providers page
- **THEN** its settings show a limit warm-up switch reflecting the opt-in
- **AND** the latest attempt status, window, model, and completion/attempt time when available, or that no attempt
  was made

#### Scenario: Opt-in while warm-up is disabled globally
- **WHEN** global limit warm-up is known to be disabled
- **THEN** the account's warm-up switch states that nothing is sent and links to Settings

#### Scenario: Dashboard cards omit warm-up
- **WHEN** the dashboard renders Codex account cards or list rows
- **THEN** they show no limit warm-up state or toggle

#### Scenario: Warm-up controls are accessible by name
- **WHEN** an operator navigates with assistive technology
- **THEN** global and per-account warm-up toggles expose descriptive accessible names that identify the setting and
  account context

## REMOVED Requirements

### Requirement: Dashboard accounts section supports card and list views

**Reason**: The list no longer sorts and no longer shows credits or warm-up; it mirrors the cards.
**Migration**: See "Dashboard accounts offer card and list views".

### Requirement: Dashboard account cards show live credit state

**Reason**: Credits appear only in the Codex card footer; the list no longer shows or sorts them.
**Migration**: See "Codex dashboard cards show subscription and purchased credits".

### Requirement: Dashboard accounts section shows account availability summary

**Reason**: The header hint counts ready, limited, paused and sign-in accounts across all providers.
**Migration**: See "Dashboard accounts header counts account states".

### Requirement: Dashboard usage donuts present credits as stacked remaining and capacity

**Reason**: The donut panels are replaced by the remaining quota card.
**Migration**: See "Dashboard remaining quota card".
