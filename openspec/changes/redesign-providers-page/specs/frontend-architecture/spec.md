## RENAMED Requirements
- FROM: `### Requirement: Accounts page`
- TO: `### Requirement: Providers page`
- FROM: `### Requirement: Accounts page unified export action`
- TO: `### Requirement: Account detail unified export action`
- FROM: `### Requirement: Accounts page exposes a reset-credits redeem action`
- TO: `### Requirement: Account detail exposes a reset-credits redeem action`
- FROM: `### Requirement: AccountListItem displays a reset-credits count badge`
- TO: `### Requirement: Account list rows display a reset-credits count badge`
- FROM: `### Requirement: Dashboard empty accounts include a CTA to Accounts`
- TO: `### Requirement: Dashboard empty accounts include a CTA to Providers`

## MODIFIED Requirements

### Requirement: Providers page

The Providers page SHALL list every account at `/providers` and show one account at `/providers/:accountId`. The
list SHALL be one table grouped by provider (Codex, Claude, Antigravity, OpenRouter, OpenAI-compatible) whose rows show
the account name with provider mark and plan, its status, two limit meters with reset countdowns, today's requests and
estimated cost, and its routing policy. The list SHALL offer search, an All / Needs attention / Paused filter with
counts, the account sort modes, an Add account button, an add control per provider group, and an add control for each
provider that has no account yet. A row SHALL link to the account's detail page; its menu SHALL offer Open, Open in
Logs and Copy ID.

The detail page SHALL show a header with the account name, plan, status, identity subline, primary actions and a menu
with Copy ID, Open in Logs and the provider's export and delete actions; a banner when the account is paused, limited
or needs re-authentication; and the provider's cards in a main and a side column using one shared frame for every
provider. On desktop widths a sticky, collapsible rail SHALL list all accounts grouped by provider with bold names,
equal-height entries, a search field, an "All providers" link and arrow-key navigation; its collapsed state SHALL
persist locally. On narrow widths the breadcrumb SHALL offer an account switcher instead. An unknown account ID SHALL
show an "Account not found" state with a link back to the list. The page SHALL also let operators view and update
whether an account is authorized for upstream cybersecurity work.

The layout SHALL fit mobile, tablet, and desktop dashboard widths without horizontal page overflow caused by fixed-width
account controls.

Account status displays SHALL distinguish `reauth_required` accounts from `deactivated` accounts:
`reauth_required` means the local credential/session must be refreshed by operator re-authentication, while
`deactivated` means the upstream account is disabled, suspended, deleted, or explicitly deactivated.

#### Scenario: Account security-work authorization is toggled

- **WHEN** an operator toggles Trusted Access for Cyber for an account
- **THEN** the app sends the account update request with the requested `securityWorkAuthorized` value
- **AND** the account list and dashboard overview data are invalidated after the update succeeds

#### Scenario: Security-work authorization appears in account summaries

- **WHEN** an account summary has `securityWorkAuthorized=true`
- **THEN** the account detail page shows that account as eligible for Trusted Access for Cyber routing

#### Scenario: Same-email workspace slots are distinguishable

- **WHEN** the account list contains multiple accounts with the same email
- **AND** at least one account has workspace metadata
- **THEN** the list and detail views show workspace identity or compact account id context sufficient to distinguish the credential slots

#### Scenario: Same-login workspace slots are preserved

- **WHEN** multiple imported or OAuth-completed credentials share the same ChatGPT account identity
- **AND** they carry distinct workspace ids or workspace labels
- **THEN** each workspace credential is preserved as a separate local account slot

#### Scenario: Import copy reflects credential slots

- **WHEN** a user views import settings
- **THEN** the copy describes preserving separate workspace or unknown credential slots instead of email-level duplicates

#### Scenario: Row opens the account

- **WHEN** an operator activates a Claude account row in the providers table
- **THEN** the browser navigates to `/providers/<account id>`
- **AND** the Claude detail page renders beside the rail with that account highlighted

#### Scenario: Add account remains outside account list scrolling

- **WHEN** the providers table renders
- **THEN** the Add account button is in the page header, not inside the table
- **AND** the button remains available without scrolling through existing accounts

#### Scenario: Long account list scrolls inside the left panel

- **WHEN** a detail page renders more accounts than fit in the rail
- **THEN** the rail's account entries scroll inside the rail
- **AND** the "All providers" link and search field remain visible outside that scroll region

#### Scenario: Needs attention filter

- **WHEN** an operator selects Needs attention
- **THEN** the table shows only accounts that are limited, need re-authentication, are deactivated or have stale monitoring
- **AND** provider groups without such accounts are hidden

#### Scenario: Responsive account management layout

- **WHEN** an account detail page is rendered at a mobile-width viewport
- **THEN** the rail is hidden and the breadcrumb offers an account switcher
- **AND** the cards stack in one column and fit within the viewport without horizontal document overflow

#### Scenario: Unknown account

- **WHEN** an operator opens `/providers/missing`
- **THEN** the page shows "Account not found" with a link to `/providers`

#### Scenario: Re-authentication-required account is labeled separately

- **WHEN** an account summary has `status = "reauth_required"`
- **THEN** the list row and the detail header show `Re-auth required`
- **AND** the account appears under the Needs attention filter
- **AND** the detail page exposes the re-authenticate action in its banner
- **AND** the detail page does not expose pause or resume actions that could bypass re-authentication
- **AND** the detail page does not expose routing-policy controls that imply the account is selectable while operator recovery is required

### Requirement: Accounts list surfaces quota reset timing

The providers table and the account rail SHALL render the weekly and 5h quota of accounts that have both windows,
each with the time remaining until reset when a reset timestamp is available. Weekly-only accounts SHALL omit the 5h
meter. The table's routing column SHALL show whether the account is opted in to limit warm-up.

#### Scenario: Regular account shows both quota rows
- **WHEN** the table renders an account with both primary and weekly quota windows
- **THEN** the row shows both 5h and weekly meters
- **AND** each rendered meter shows its reset countdown

#### Scenario: Weekly-only account omits the 5h row
- **WHEN** the table renders an account whose primary window is absent
- **THEN** the row does not render a 5h meter
- **AND** the weekly meter still renders

#### Scenario: Limit warm-up opt-in is visible
- **WHEN** the table renders an account with limit warm-up opt-in enabled
- **THEN** the routing column shows the opt-in state

### Requirement: Accounts list supports explicit sort modes

The providers table SHALL expose sort modes for reset time soonest-first, reset time latest-first, account name
ascending, and account name descending. The selected sort mode SHALL order the accounts within each provider group,
and the account rail SHALL use the same order.

#### Scenario: Reset soonest remains the default

- **WHEN** a user selects reset time soonest-first
- **THEN** accounts with the earliest upcoming visible quota reset sort first within each provider group

#### Scenario: Reset latest sorts finite resets descending

- **WHEN** a user selects reset time latest-first
- **THEN** accounts with later upcoming visible quota resets sort before
  accounts with earlier upcoming visible quota resets
- **AND** accounts without an upcoming visible reset timestamp sort after
  accounts with finite upcoming reset timestamps

#### Scenario: Name sort modes order by account label

- **WHEN** a user selects account name ascending or descending
- **THEN** the table orders accounts by display name, email, or account
  identifier in the selected direction within each provider group

### Requirement: Account detail unified export action

The Codex account detail menu SHALL offer one "Export credentials" item. Selecting it SHALL call
`POST /api/accounts/{id}/export/auth` and, on success, open a modal dialog titled "Auth Export" with a format mode
selector ("codex" / "opencode") and the full response. No auto-download SHALL occur without user interaction in the
modal.

#### Scenario: Single export button replaces dual buttons

- **WHEN** a user opens the menu of a Codex account detail
- **THEN** exactly one "Export credentials" item is present
- **AND** no separate "Export OpenCode auth" action is present

#### Scenario: Export opens modal after API success

- **WHEN** a user selects "Export credentials"
- **THEN** the frontend calls `POST /api/accounts/{id}/export/auth`
- **AND** on success the "Auth Export" modal opens with the response data
- **AND** no file is downloaded until the user clicks Download in the modal

#### Scenario: Export error shows toast

- **WHEN** the `POST /api/accounts/{id}/export/auth` call fails
- **THEN** a toast notification shows the error message
- **AND** no modal opens

### Requirement: Account list presents a single add-account entry point with a chooser dialog

Every add control on the Providers page (the Add account button, a provider group's add control and a "not connected
yet" provider chip) SHALL open the same chooser dialog with two groups. "Subscriptions" SHALL list Codex, Claude and
Antigravity in that order, each labelled with its provider logo and offering exactly two options, "Sign in" and
"Import file". "API providers" SHALL list OpenRouter and OpenAI-compatible, each one option with its provider logo as
icon. Every option SHALL close the chooser and open exactly one dialog for one method.

#### Scenario: Add-account placeholder opens the chooser

- **WHEN** an operator activates "Add account", a provider group's add control or a "not connected yet" chip
- **THEN** the chooser shows Subscriptions (Codex, Claude, Antigravity) and API providers (OpenRouter, OpenAI-compatible)

#### Scenario: Choosing an option opens its existing flow

- **WHEN** the operator selects "Import file" under Claude
- **THEN** the chooser closes and only the Claude credential import dialog opens

### Requirement: Account detail exposes a reset-credits redeem action

The Codex account detail header SHALL render a `Reset (N)` action whenever the account reports
`available_reset_credits > 0`, where `N` is the available reset-credit count; when the account's limit is reached the
action SHALL be shown in the limit banner instead. The action SHALL be hidden when `available_reset_credits` is `0`.
Activating it SHALL open a confirmation dialog that describes redeeming the soonest-expiring banked reset credit for
that account and, when credit details are available, shows the soonest credit's expiry in local time using
`YYYY-MM-DD HH:MM:SS`. Confirming SHALL submit a redeem request for that account and refresh account data on success.
The compact remaining-time label pinned to the reset action SHALL be controlled by the dashboard setting
`show_reset_credit_expiry_badge`, defaulting to enabled.

#### Scenario: Reset button mirrors Export styling and placement
- **WHEN** the detail page renders a Codex account with `available_reset_credits > 0` whose limit is not reached
- **THEN** a `Reset (N)` button appears among the header actions
- **AND** the button uses the same size, variant, and class as the other header actions

#### Scenario: Reset action in the limit banner
- **WHEN** the account's limit is reached and it has `available_reset_credits > 0`
- **THEN** the `Reset (N)` button appears in the limit banner and not among the header actions

#### Scenario: Reset button hidden when no credits available
- **WHEN** an account reports `available_reset_credits: 0`
- **THEN** the detail page renders no "Reset" button

#### Scenario: Confirmation required before redeem
- **WHEN** the operator clicks the "Reset" button
- **THEN** a confirmation dialog opens describing the soonest-expiring banked reset-credit redeem action
- **AND** no redeem request is sent until the operator confirms

#### Scenario: Confirmation dialog shows local expiry timestamp
- **WHEN** the operator opens the reset-credit confirmation dialog and credit details include an expiry timestamp
- **THEN** the dialog renders the credit expiry in local time using `YYYY-MM-DD HH:MM:SS`

#### Scenario: Reset action expiry label can be hidden
- **GIVEN** `show_reset_credit_expiry_badge` is disabled
- **AND** an account reports `available_reset_credits > 0` and `reset_credit_nearest_expires_at`
- **WHEN** the detail page renders
- **THEN** the `Reset (N)` button remains visible
- **AND** the compact remaining-time label is not rendered on that button

### Requirement: Account list rows display a reset-credits count badge

A providers table row SHALL render a count badge after the account name whenever the account reports
`available_reset_credits > 0` and dashboard setting `show_reset_credit_badges` is enabled. The badge SHALL display the
integer count, capped visually at `"99+"` when the count exceeds 99. The badge SHALL be absent when
`available_reset_credits` is `0` or `show_reset_credit_badges` is disabled.

#### Scenario: Badge shows the available count
- **WHEN** a row renders for an account with `available_reset_credits: 3`
- **THEN** a count badge after the account name displays `3`

#### Scenario: Badge caps at 99+
- **WHEN** a row renders for an account with `available_reset_credits: 120`
- **THEN** the count badge displays `99+`

#### Scenario: Badge absent when zero
- **WHEN** a row renders for an account with `available_reset_credits: 0`
- **THEN** no count badge is rendered

#### Scenario: Badge visibility follows settings
- **GIVEN** `show_reset_credit_badges` is disabled
- **AND** an account reports `available_reset_credits: 3`
- **WHEN** a row renders
- **THEN** the reset-credit count badge is absent

### Requirement: Dashboard empty accounts include a CTA to Providers

The dashboard empty-account cards and list SHALL include a control that
navigates to `/providers` when the overview has no accounts.

#### Scenario: Empty account cards link to Accounts

- **GIVEN** the dashboard overview has no accounts
- **WHEN** the account cards empty state renders
- **THEN** the empty state includes a link to `/providers`

#### Scenario: Empty account list links to Accounts

- **GIVEN** the dashboard overview has no accounts
- **WHEN** the account list empty state renders
- **THEN** the empty state includes a link to `/providers`

## ADDED Requirements

### Requirement: Provider rail stays within the viewport

The account rail on a detail page MUST stay above the fixed status bar both before and after the page scrolls, and a
rail with more accounts than fit MUST scroll internally while its "All providers" link and search field stay visible.

#### Scenario: Long account pool

- **WHEN** a detail page opens with 40 accounts in a 1200px-tall desktop viewport
- **THEN** the rail's account entries scroll inside the rail
- **AND** the rail ends at least 8px above the fixed status bar
- **AND** the "All providers" link remains visible

### Requirement: Account detail shows recent activity

Every account detail page SHALL show a "Last 7 days" card that charts the account's daily estimated cost or requests,
switchable between the two, from `GET /api/reports` `dailyByAccount`, and SHALL total its requests (with today's
count), estimated cost (with today's cost), tokens and errors. The errors total SHALL link to the account's request
logs. When the report cannot be loaded the card SHALL say that activity is unavailable.

#### Scenario: Errors link to logs

- **WHEN** an account had two failed requests in the last seven days
- **THEN** the card's errors total shows 2
- **AND** activating it opens Logs filtered to that account

## REMOVED Requirements

### Requirement: Account list status filter shares the help row

**Reason**: The status select is replaced by the All / Needs attention / Paused filter in the providers table toolbar,
described in "Providers page".
**Migration**: None.

### Requirement: Accounts list uses available tall-viewport space

**Reason**: The list is a full-page table instead of a bounded side list; the bounded account list on detail pages is
covered by "Provider rail stays within the viewport".
**Migration**: None.

### Requirement: Accounts page selects the first listed account

**Reason**: The list page has no selection; an account is shown only at its own `/providers/:accountId` address.
**Migration**: Links that used `/accounts?selected=<id>` use `/providers/<id>`.
