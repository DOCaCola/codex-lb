# frontend-architecture Specification

## Purpose

Define dashboard surface contracts so settings, account management, and operational views stay coherent across the SPA.

## Requirements

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
or needs re-authentication; and an Overview and a Settings tab, using one shared frame for every provider. The
Overview tab SHALL show usage and activity in a main column and status and details in a side column. The Settings tab
SHALL show the account's options (routing, models, capacity, proxy binding, client version identity, connection) in
stacked full-width cards. The Settings tab SHALL be addressed by `/providers/:accountId/settings`. On desktop widths a
sticky, collapsible rail SHALL list all accounts grouped by provider with bold names, equal-height entries, a search
field, an "All providers" link and arrow-key navigation; its collapsed state SHALL persist locally. The selected rail
entry SHALL use the shared selection style, not the account's chart colour. Switching accounts through the rail or the
narrow-width switcher SHALL keep the open tab. On narrow widths the breadcrumb SHALL offer an account switcher
instead. An unknown account ID SHALL show an "Account not found" state with a link back to the list. The page SHALL
also let operators view and update whether an account is authorized for upstream cybersecurity work.

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

#### Scenario: Settings tab has its own address

- **WHEN** an operator selects the Settings tab of an account page
- **THEN** the browser navigates to `/providers/<account id>/settings`
- **AND** the account's routing and model controls render in full-width cards instead of the usage cards

#### Scenario: Rail keeps the open tab

- **WHEN** the Settings tab of one account is open and the operator selects another account in the rail
- **THEN** the browser navigates to `/providers/<other account id>/settings`

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

### Requirement: Request logs display account plan tier
When a request log entry is associated with an account, the dashboard request-log API response MUST expose the persisted request-log `planType` snapshot, and the recent-requests table MUST render the plan tier in a visible request-log column or badge.

#### Scenario: Request log entry keeps its original plan type snapshot
- **WHEN** a request log entry is written while the associated account's `plan_type` is `free`
- **AND** the account later changes to `team`
- **THEN** the `GET /api/request-logs` response still includes `planType: "free"` for that row
- **AND** the dashboard recent-requests table renders the original `free` plan tier visibly for that row

#### Scenario: Legacy request log entry without account still renders
- **WHEN** a request log entry has no related account
- **THEN** the `GET /api/request-logs` response includes `planType: null` or omits it
- **AND** the dashboard recent-requests table still renders the row without failing

### Requirement: Request logs distinguish actual and requested service tiers
When a request log entry includes service-tier data, the dashboard request-log API response MUST expose the billable tier, requested tier, and actual tier separately. The recent-requests UI MUST present the billable tier: Fast (`priority`) and Ultrafast as a grey tier icon next to the reasoning effort, other non-standard tiers as muted text, and the standard `default`/`auto` tier not at all. The UI MUST show a downgrade note only when the billable tier is cheaper than the requested tier.

#### Scenario: Dashboard shows upstream-selected tier and requested tier
- **WHEN** a request log entry is recorded with `requested_service_tier: "priority"`, `actual_service_tier: "default"`, and billable `service_tier: "priority"`
- **THEN** the `GET /api/request-logs` response includes `requestedServiceTier: "priority"`, `actualServiceTier: "default"`, and `serviceTier: "priority"`
- **AND** the dashboard renders the grey Fast icon next to the model label
- **AND** no downgrade note is shown

#### Scenario: Proven downgrade
- **WHEN** a request log entry is recorded with `requested_service_tier: "priority"` and billable `service_tier: "flex"`
- **THEN** the dashboard shows that Fast was requested and Flex was billed

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

### Requirement: Accounts list respects compact row appearance preference
The Accounts page account list SHALL honor a locally stored appearance preference that selects which compact quota rows are shown: 5h, weekly, or both. The default preference SHALL be Both. When the selected row is unavailable for a given account, the list MAY fall back to the available row so the account still shows quota information.

#### Scenario: Default preference shows both rows
- **WHEN** the appearance preference is unset
- **THEN** the account list shows both 5h and weekly rows for accounts that have both quota windows

#### Scenario: 5h preference shows only the 5h row
- **WHEN** the appearance preference is set to 5H
- **THEN** the account list shows the 5h row and hides the weekly row for accounts that have both quota windows

#### Scenario: Weekly preference shows only the weekly row
- **WHEN** the appearance preference is set to W
- **THEN** the account list shows the weekly row and hides the 5h row for accounts that have both quota windows

### Requirement: Accounts list orders by next reset
The Accounts page account list SHALL order accounts by the earliest upcoming quota reset timestamp among the rendered quota windows. Accounts without any reset timestamp SHALL sort after accounts with a reset timestamp. When reset timestamps are equal or unavailable, the list MAY fall back to a stable text-based order.

#### Scenario: Earlier reset sorts first
- **WHEN** two accounts are shown in the account list and one account has an earlier quota reset time than the other
- **THEN** the earlier-reset account appears before the later-reset account

### Requirement: Dashboard request-log filtering supports API keys

The dashboard request logs view SHALL allow operators to filter rows by one or more API keys using stable API key identifiers while presenting human-readable API key labels in the UI.

#### Scenario: Apply API key request-log filter

- **WHEN** a user selects one or more API keys in the request logs filters
- **THEN** the request logs query refetches from `GET /api/request-logs` with repeated `apiKeyId` parameters
- **AND** the dashboard overview is NOT refetched

#### Scenario: Request-log API key options remain expandable

- **WHEN** a user has already selected one API key in the request logs filters
- **THEN** the API key filter options continue to show other matching API keys instead of collapsing to only the selected key
- **AND** the user can add another API key without clearing the existing selection first

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

#### Scenario: Runway card compares usage with the linear schedule

- **WHEN** the runway card renders for Codex or Claude
- **THEN** a schedule row beneath the runway timeline shows Used now (`actualUsedPercent`), Scheduled by now (`scheduledUsedPercent`), and the smoothed gap as over planned usage, below planned usage, or On pace when the gap rounds to zero percent
- **AND** its bar marks the scheduled position, stripes usage beyond the schedule, and outlines scheduled usage that has not happened yet
- **AND** when `smoothedScheduleGapCredits` is positive the row states that amount over planned usage over the smoothing window, in credits for Codex and Pro units for Claude
- **AND** the row stays neutral in every state because status emphasis belongs to the runway verdict

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
- **THEN** the response reports additional Pro accounts (Codex) or Pro-equivalents (Claude) computed from the weekly demand surplus
- **AND** the figure does not change materially from hour to hour under steady traffic

#### Scenario: Throttle guidance precedes purchase guidance

- **WHEN** the runway verdict is `runs_dry`
- **AND** `throttleToPercent` is available
- **THEN** neither card layout presents a recommendations section
- **AND** the response keeps the throttle, pause and add-capacity figures for API consumers

#### Scenario: Card paints without the projections request

- **WHEN** the overview response has arrived and the projections request is still in flight or failed
- **THEN** the weekly runway card renders its full content from the overview payload with a stable layout footprint

### Requirement: Weekly consumer estimated API costs

The dashboard SHALL show a standalone Top consumers card listing the top API keys by requests and by billable tokens over the trailing two hours, with request count, billable tokens, dominant model and compact USD estimated API cost. The overview and projections payloads SHALL provide the lists per provider (`topConsumers.codex` from native Codex requests, `topConsumers.claude` from Claude requests and `topConsumers.antigravity` from Antigravity requests), and the card SHALL show the list of the selected quota provider. Costs SHALL use recorded request costs across all models and existing coverage rules, never a quota-credit conversion. Unknown, free and incomplete costs SHALL remain distinct, with incomplete details in tooltips. Runway calculations and privacy rules SHALL remain unchanged.

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

### Requirement: Concise dashboard account subtitles

Dashboard account cards SHALL omit model-selection counts and All models labels
from their subtitles. They SHALL retain known provider/plan identity and use the
middle-dot separator between multiple fields, including optional account IDs.
Shared card anatomy, privacy and account actions SHALL remain unchanged. Model
selection controls elsewhere SHALL remain available.

#### Scenario: Provider card subtitles
- **WHEN** Codex Plus, paid OpenRouter and Claude Pro accounts are shown
- **THEN** their subtitles read Plus, OpenRouter · Paid and Claude · Pro respectively, without selected-model counts

### Requirement: Account weekly trend planned line

The account detail usage trend SHALL include an ideal weekly remaining line when weekly reset timing is available, so operators can compare actual weekly remaining credits against the linear schedule between weekly resets.

#### Scenario: Weekly trend shows planned depletion between resets

- **WHEN** account trend buckets include weekly reset time and window length
- **THEN** the account 7-day trend includes a dashed weekly plan line computed from each bucket's reset deadline and window length

#### Scenario: Weekly trend plan restarts after reset

- **WHEN** weekly trend buckets cross into a new reset window with a new reset deadline
- **THEN** the planned line jumps back toward full remaining capacity for the new weekly window instead of continuing one global diagonal

### Requirement: Dashboard request-log list excludes deleted-account rows

When an account is deleted, request-log rows that were soft-deleted as part of that account removal MUST NOT appear in the dashboard request-log list or request-log filter-option facets.

#### Scenario: Deleted account log hidden from recent request rows

- **GIVEN** a request log row was previously associated with an account
- **AND** deleting that account soft-deleted the row
- **WHEN** a user loads `GET /api/request-logs`
- **THEN** the soft-deleted row is not included in the `requests` payload

#### Scenario: Deleted account log hidden from request-log facets

- **GIVEN** a request log row was previously associated with an account
- **AND** deleting that account soft-deleted the row
- **WHEN** a user loads `GET /api/request-logs/options`
- **THEN** the soft-deleted row does not contribute account, model, API-key, or status facet options

### Requirement: Dashboard overview metrics keep soft-deleted request logs

Dashboard overview request metrics and trends MUST continue to aggregate soft-deleted request-log rows so account deletion does not rewrite historical request activity.

#### Scenario: Deleted account log still counted in overview metrics

- **GIVEN** an account has request-log activity within the active overview timeframe
- **AND** the account is deleted afterward
- **WHEN** a user loads `GET /api/dashboard/overview`
- **THEN** request-derived metrics and trends still include that historical request-log activity

### Requirement: Dashboard settings page exposes password session lifetime

The SPA settings page SHALL expose a dashboard password session lifetime control for operators when password management is enabled. The control SHALL display the current configured lifetime, validate an operator-supplied value against the backend minimum, and save the new lifetime through the existing settings API. When the configured lifetime exceeds 30 days, the SPA SHALL show a warning that the longer lifetime increases the impact of a leaked browser profile or stolen cookie.

#### Scenario: Admin updates dashboard password session lifetime

- **WHEN** an admin opens the Settings page and changes the dashboard session lifetime value
- **THEN** the SPA submits the updated lifetime through `/api/settings`
- **AND** the saved settings response reflects the new lifetime value

#### Scenario: Admin chooses a long dashboard session lifetime

- **WHEN** an admin enters a dashboard session lifetime greater than 30 days
- **THEN** the Settings page shows a warning explaining that the longer lifetime increases the impact of a leaked browser profile or stolen cookie
- **AND** the admin can still save the configured lifetime

### Requirement: Account summary duplicate email indicator

The dashboard accounts API SHALL expose an `isEmailDuplicate` boolean on each
`AccountSummary` returned by `GET /api/accounts`. The field MUST be `true` when
another account row in the same response has the same real email address and
the same ChatGPT account identity, and MUST be `false` for unique real
email/identity pairs. Missing, blank, and legacy placeholder emails equal to
`DEFAULT_EMAIL` (`unknown@example.com`) MUST be excluded from duplicate
detection and MUST NOT be flagged as duplicates. Rows that share an email but
belong to different ChatGPT account identities MUST NOT be flagged as
duplicates.

#### Scenario: Duplicate real email and identity pairs are flagged

- **WHEN** `GET /api/accounts` returns two or more account rows with the same real non-placeholder email and the same ChatGPT account identity
- **THEN** every row in that email and identity group includes `isEmailDuplicate: true`

#### Scenario: Same email across identities is not flagged

- **WHEN** `GET /api/accounts` returns account rows with the same real non-placeholder email but different ChatGPT account identities
- **THEN** those rows include `isEmailDuplicate: false`

#### Scenario: Placeholder emails are ignored

- **WHEN** `GET /api/accounts` returns two or more account rows whose email is `unknown@example.com`
- **THEN** those rows include `isEmailDuplicate: false`

#### Scenario: Unique emails are not flagged

- **WHEN** `GET /api/accounts` returns an account row with an email that appears only once in the response
- **THEN** that row includes `isEmailDuplicate: false`

### Requirement: Dashboard projections load after the primary dashboard data

The dashboard SPA SHALL render primary dashboard content from `GET /api/dashboard/overview`
and recent request-log data without waiting for depletion or weekly-credit projection
calculations. Projection-only data, including safe-line depletion markers and weekly-credit
pace, SHALL be available from `GET /api/dashboard/projections` and fetched after overview
data is available.

#### Scenario: Main dashboard renders before projections finish

- **GIVEN** an authenticated operator opens the dashboard
- **WHEN** `GET /api/dashboard/overview` and request-log calls complete before `GET /api/dashboard/projections`
- **THEN** the dashboard renders the primary cards, usage donuts, account list, and request-log surface
- **AND** projection-only safe-line and weekly-credit fields may populate later when the projections response arrives

#### Scenario: Projection endpoint exposes heavy dashboard calculations

- **WHEN** the dashboard client requests `GET /api/dashboard/projections`
- **THEN** the response includes depletion safe-line data and weekly-credit pace data when those calculations are available
- **AND** the overview endpoint does not need to compute those fields for initial page render

### Requirement: Footer version update indicator

The dashboard footer SHALL show the running application version and SHALL display a compact update-available icon next to that version only when the runtime version API confirms a newer stable GitHub release exists.

#### Scenario: Newer release is available

- **WHEN** `GET /api/runtime/version` returns `updateAvailable: true` with a `latestVersion`
- **THEN** the footer renders an accessible update icon beside the current version
- **AND** the icon links to `https://github.com/Soju06/codex-lb/releases/latest`
- **AND** the icon title or accessible label includes the latest version

#### Scenario: Version lookup is unavailable

- **WHEN** `GET /api/runtime/version` fails or returns no newer version
- **THEN** the footer continues showing the current version without an update indicator

### Requirement: Delete account with history purge

The account delete confirmation dialog SHALL include a checkbox labeled "Delete all history for this account". When checked and the delete action is confirmed, all associated data (request_logs, usage_history, sticky_sessions) SHALL be hard-deleted from the database instead of soft-deleted. When unchecked, the existing soft-delete behavior SHALL apply.

#### Scenario: Delete with history checkbox checked

- **WHEN** an operator opens the delete confirmation dialog for an account and checks "Delete all history for this account"
- **AND** clicks the confirm/Delete button
- **THEN** the `DELETE /api/accounts/{account_id}` request includes `?delete_history=true`
- **AND** all `request_logs` rows for the account are hard-deleted from the database
- **AND** `usage_history` rows for the account are hard-deleted (existing behavior)
- **AND** the account itself is deleted
- **AND** the UI shows a success toast and refreshes the account list

#### Scenario: Delete with history checkbox unchecked

- **WHEN** an operator opens the delete confirmation dialog and does NOT check "Delete all history for this account"
- **AND** clicks the confirm/Delete button
- **THEN** the `DELETE /api/accounts/{account_id}` request omits the `delete_history` parameter
- **AND** `request_logs` rows are soft-deleted (account_id=NULL, deleted_at set)
- **AND** all other behavior is identical to current account deletion

#### Scenario: Cancel the delete dialog

- **WHEN** an operator opens the delete confirmation dialog
- **AND** clicks the Cancel button
- **THEN** the dialog closes and no API request is made
- **AND** the account remains in the list unchanged

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

### Requirement: Account alias contract

The dashboard accounts API SHALL expose an operator-controlled, human-readable `alias` on every account summary, and SHALL provide an endpoint that lets an authenticated dashboard session set or clear that alias. The alias MUST be persisted on the `Account` record and MUST be reflected in `AccountSummary.alias`. When a non-empty alias is set, the same `AccountSummary.display_name` field MUST resolve to the alias so consumers that already render `display_name` see the operator's chosen label without further changes. When the alias is null or cleared, `display_name` MUST fall back to the account's email so existing UI continues to identify the account.

#### Scenario: Listing surfaces the alias when set

- **WHEN** the dashboard requests `GET /api/accounts` and at least one account has a stored alias
- **THEN** that account's summary includes `alias` with the stored value
- **AND** its `display_name` equals the alias

#### Scenario: Listing falls back to email when alias is null

- **WHEN** the dashboard requests `GET /api/accounts` and an account has no stored alias
- **THEN** that account's summary includes `alias: null`
- **AND** its `display_name` equals the account's email

#### Scenario: Setting an alias persists and trims whitespace

- **WHEN** an authenticated dashboard session calls `PUT /api/accounts/{account_id}/alias` with `{"alias": "  Personal Plus  "}`
- **THEN** the response is 200 with `{"account_id": "...", "alias": "Personal Plus"}`
- **AND** subsequent `GET /api/accounts` reflects the trimmed value on both `alias` and `display_name`

#### Scenario: Empty or whitespace-only alias clears the value

- **WHEN** an authenticated dashboard session calls `PUT /api/accounts/{account_id}/alias` with `{"alias": ""}` or `{"alias": "   "}`
- **THEN** the response is 200 with `{"alias": null}`
- **AND** subsequent `GET /api/accounts` shows `alias: null` and `display_name` reverting to the account's email

#### Scenario: Setting alias on an unknown account returns 404

- **WHEN** `PUT /api/accounts/{account_id}/alias` is called with an `account_id` that does not exist
- **THEN** the response is 404 with error code `account_not_found`

#### Scenario: Dashboard UI edits and searches aliases

- **WHEN** an operator opens the dashboard accounts page and selects an account
- **THEN** the account detail panel provides an `Account alias` control that can save a non-empty alias through `PUT /api/accounts/{account_id}/alias`
- **AND** clearing the control stores `alias: null` and restores the email fallback
- **AND** account search matches the stored alias or alias-backed display name so operators can filter duplicate-email accounts by their chosen label

### Requirement: Dashboard account summaries sorted by primary capacity

The dashboard overview API MUST return account summaries sorted by `capacity_credits_primary` in descending order so the highest-capacity accounts appear first. Accounts with no primary capacity MUST sort after accounts that have one.

#### Scenario: Accounts ordered by primary capacity

- **WHEN** the dashboard overview response includes multiple accounts with different `capacity_credits_primary` values
- **THEN** accounts are ordered from highest to lowest primary capacity

#### Scenario: Accounts without primary capacity sort last

- **WHEN** an account has `capacity_credits_primary` of `null` or `0`
- **THEN** that account appears after accounts with a positive primary capacity

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

### Requirement: Weekly credits pace header uses flex-start alignment

The weekly credits pace card header MUST align the title and gauge icon to the flex start, not vertically centered.

#### Scenario: Header alignment

- **WHEN** the weekly credits pace card renders
- **THEN** the header row uses `justify-between` without `items-center`

### Requirement: Request logs expose cost breakdown details
When a request log has sufficient usage data, the dashboard request-log API MUST expose raw input/output token counts and a cost breakdown that separates non-cached input, cached input, and output cost.

#### Scenario: Successful request log exposes token and cost segments
- **WHEN** a successful request log row has persisted input, cached-input, and output usage
- **THEN** `GET /api/request-logs` includes `inputTokens`, `outputTokens`, and `costBreakdown`
- **AND** `costBreakdown` includes `inputUsd`, `cachedInputUsd`, `outputUsd`, and `totalUsd`

#### Scenario: Request log output falls back to reasoning tokens
- **WHEN** a successful request log row has no persisted `output_tokens` and does have `reasoning_tokens`
- **THEN** `GET /api/request-logs` uses the reasoning-token value for `outputTokens`

#### Scenario: Request log response preserves shape for legacy partial data
- **WHEN** a successful request log row is missing one or more persisted token or cost segments
- **THEN** `GET /api/request-logs` still includes `inputTokens`, `outputTokens`, and `costBreakdown`
- **AND** any unavailable top-level token field is returned as `null`
- **AND** `costBreakdown` includes `inputUsd`, `cachedInputUsd`, `outputUsd`, and `totalUsd`
- **AND** any unavailable `costBreakdown` field is returned as `null`
- **AND** clients can render only the available token and cost segments without treating the row as invalid

### Requirement: Request detail dialog renders successful cost breakdowns
The dashboard request-log `View Details` dialog MUST render a `Cost` section under `Archive` for successful request rows and MUST hide the section for non-success rows.

#### Scenario: Successful request displays ordered cost details
- **WHEN** a request log detail dialog opens for an `ok` row with available breakdown data
- **THEN** the dialog displays the total cost first
- **AND** the dialog lists available cost segments in this order: input, cached, output
- **AND** each displayed segment includes its token count and matching currency value
- **AND** token counts use the same compact formatting as the request-log tokens column
- **AND** currency values are rounded to two decimals

#### Scenario: Missing cost segments are omitted without breaking the dialog
- **WHEN** a successful request log row is missing one or more token or cost segments
- **THEN** the dialog renders only the available segments
- **AND** if no segments are available the `Cost` section is hidden

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

### Requirement: Reports page loads report data from the reports endpoint

The `/reports` page SHALL load and refetch report data from `GET /api/reports`.

#### Scenario: Reports page loads from reports endpoint

- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page loads report data from `GET /api/reports`

#### Scenario: Reports page refetches from reports endpoint

- **WHEN** an authenticated operator changes a report filter on `/reports`
- **THEN** the page refetches report data from `GET /api/reports`

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

### Requirement: Reports page preserves reports query parameter names

Requests from `/reports` to `GET /api/reports` SHALL use the query parameter names `startDate`, `endDate`, `accountId`, and `model`.

#### Scenario: Reports page uses preserved reports query parameter names

- **WHEN** an authenticated operator opens `/reports` or changes a report filter
- **THEN** the request uses `startDate`, `endDate`, `accountId`, and `model` as the query parameter names

### Requirement: Reports chart tooltip uses recharts TooltipContentProps

The reports `ChartTooltip` component SHALL type its props as `Partial<TooltipContentProps>` from recharts so that context-injected properties (`payload`, `active`, `label`, `coordinate`) are optional at the JSX call site while remaining correctly typed inside the component body.

#### Scenario: ChartTooltip renders without context props at the JSX call site

- **WHEN** a reports chart passes `<ChartTooltip names={...} formatValue={...} />` via the recharts `<Tooltip content={...}>` prop
- **THEN** TypeScript compilation succeeds without errors about missing `payload`, `active`, `label`, or `coordinate`
- **AND** recharts injects those properties at runtime before calling the component

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

### Requirement: Reset-window routing setting UI
The dashboard routing settings UI SHALL expose a control for the earlier-reset
preference window whenever earlier-reset routing preference is configurable. The
control SHALL allow only `primary` and `secondary` values and SHALL submit the
selected value using the settings API field `preferEarlierResetWindow`.

#### Scenario: Operator selects primary reset window
- **GIVEN** the routing settings UI is open
- **WHEN** the operator selects `primary` as the earlier-reset window
- **THEN** the settings update payload includes `preferEarlierResetWindow: "primary"`

#### Scenario: Imported settings preserve reset-window preference
- **GIVEN** an imported settings payload includes `preferEarlierResetWindow`
- **WHEN** the settings import is applied
- **THEN** the imported value is sent to the backend instead of being dropped

### Requirement: Dashboard settings must expose upstream proxy routing controls
The settings dashboard MUST allow operators to inspect upstream proxy routing state, enable or disable routing, choose the default proxy pool, create proxy endpoints, create proxy pools, and add endpoints to pools. For every endpoint the admin API reports as `plaintextCredentials: true`, the endpoint list MUST render a warning stating that its credentials are sent unencrypted over that scheme and recommending an `https://` proxy or a credential-free IP allowlist; endpoints reported as `false` MUST render no such warning.

#### Scenario: Operator creates a pool from existing endpoints
- **GIVEN** the upstream proxy admin API returns at least one endpoint
- **WHEN** an operator creates a pool and selects endpoint members
- **THEN** the dashboard MUST call the pool creation API with the selected endpoint ids
- **AND** refresh the displayed upstream proxy admin state.

#### Scenario: Plaintext-credential endpoint shows a warning

- **GIVEN** the upstream proxy admin API returns an endpoint with `plaintextCredentials: true`
- **WHEN** the upstream proxy settings section renders
- **THEN** that endpoint's row shows the plaintext-credential warning naming its scheme

#### Scenario: Encrypted or credential-free endpoint shows no warning

- **GIVEN** the upstream proxy admin API returns an endpoint with `plaintextCredentials: false`
- **WHEN** the upstream proxy settings section renders
- **THEN** that endpoint's row shows no plaintext-credential warning

### Requirement: Dashboard accounts must expose account proxy bindings
The accounts dashboard MUST allow operators to bind an account to a proxy pool and disable an existing account binding.

#### Scenario: Operator binds an account to a pool
- **GIVEN** upstream proxy routing has at least one proxy pool
- **WHEN** an operator selects a pool for an account and saves the binding
- **THEN** the dashboard MUST call the account binding API for that account
- **AND** display the selected pool as the account binding.

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

### Requirement: API key overview SHALL show lifetime usage aggregates

The API Keys page SHALL present the API key list `usageSummary` values as lifetime aggregates (all non-warmup
request-log history), unless the backend contract is changed to provide a bounded window explicitly. The header
summary SHALL show the lifetime cost of all keys, each table row SHALL show its key's lifetime cost, share of the
lifetime cost of all keys and request count, and a key's Overview tab SHALL show its lifetime requests, tokens and
cost with that share.

#### Scenario: Overview usage labels reflect lifetime scope

- **WHEN** the page renders `usageSummary` values for request count, token count, and cost
- **THEN** those values are labeled as lifetime usage, not as 7-day totals

#### Scenario: Lifetime share of all keys

- **WHEN** two keys have lifetime costs of $30 and $10
- **THEN** their rows show shares of 75% and 25%

### Requirement: Dashboard request-log details expose user-agent metadata
The dashboard request-log API response MUST expose the persisted request-log `useragent` and `useragentGroup` values when present. The Request Details dialog MUST render the full `useragent` value in a `User Agent` field below the `Transport`, `Time`, and `Error Code` row, and MUST render `—` when no full user-agent value is stored.

#### Scenario: Request details show the full stored user-agent
- **WHEN** a request log entry is stored with `useragent: "opencode/1.15.13 ai-sdk/provider-utils/4.0.23 runtime/bun/1.3.14"` and `useragentGroup: "opencode"`
- **THEN** the `GET /api/request-logs` response includes both values for that row
- **AND** the Request Details dialog shows `User Agent` with the full stored string

#### Scenario: Request details show a placeholder for legacy rows
- **WHEN** a request log entry has `useragent: null`
- **THEN** the `GET /api/request-logs` response includes `useragent: null` and `useragentGroup: null` or omits them as nullable fields
- **AND** the Request Details dialog renders `User Agent` as `—`

### Requirement: `/api/reports` returns nullable account buckets safely

`GET /api/reports` SHALL return an `accountId` field for each `byAccount` item that is either a string account identifier or `null`.
The system MUST preserve rows with `account_id IS NULL` and return them as a separate account bucket with `accountId: null` so historical usage is still represented.

#### Scenario: Null accountId is serialized for historical rows
- **WHEN** request logs in the selected period include rows with `account_id = NULL`
- **AND** those rows have non-null `cost_usd`
- **THEN** the `byAccount` response includes an item with `accountId: null`
- **AND** response serialization succeeds without schema validation failure

### Requirement: Reports data path uses backend-side date grouping

`GET /api/reports` SHALL use backend-side date grouping logic for both PostgreSQL and SQLite, producing `YYYY-MM-DD` daily buckets for stable trend display and CSV export.

#### Scenario: SQLite report request returns date buckets
- **WHEN** the repository is SQLite
- **AND** `/api/reports` is called with a valid date range
- **THEN** the response contains `daily` entries with `date` values in `YYYY-MM-DD` format
- **AND** the endpoint responds with HTTP 200

### Requirement: Reports API is accessible through the dashboard route map

The dashboard surface SHALL expose a reports page at route `/reports` and route to data loaded from `GET /api/reports`
with date-range, account, provider-account, API-key, model and user-agent filters.

#### Scenario: Dashboard reports page uses `/api/reports`
- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page loads the aggregated reports payload from `GET /api/reports`
- **AND** allows filtering by date range, account, API key, model and user agent
- **AND** uses the returned payload to render summary cards, the daily trend, breakdown lists, latency charts and the
  daily breakdown

### Requirement: Dashboard overview summary cards show previous-window usage deltas

The dashboard overview API SHALL expose previous-window comparison data for the existing `Requests`, `Tokens`, and `Est. API Cost` summary cards returned by `GET /api/dashboard/overview`. The comparison SHALL be tied to the selected overview timeframe so that `1d` compares the current 1-day window with the immediately preceding 1-day window, `7d` compares the current 7-day window with the immediately preceding 7-day window, and `30d` compares the current 30-day window with the immediately preceding 30-day window.

The overview response SHALL include a comparison block that exposes whether previous-window comparison is allowed and the previous-window totals for requests, tokens, and estimated API cost. The dashboard SHALL use that block to render a compact percentage-change indicator on the existing `Requests`, `Tokens`, and `Est. API Cost` cards only. The dashboard MUST NOT add this indicator to `Error rate` or `Account burn projection`.

If the immediately preceding window is not fully covered by eligible request-log history for the selected timeframe, the overview response SHALL mark the comparison as unavailable and the dashboard SHALL hide the percentage-change indicator for those cards.

If previous-window comparison is available and the previous total for a card is greater than zero, the dashboard SHALL calculate the displayed change from the current total relative to the previous total, SHALL show increases with an upward indicator using the project's positive `emerald` styling, and SHALL show decreases with a downward indicator using the project's negative `red` styling.

#### Scenario: Daily overview renders increase from previous window

- **WHEN** `GET /api/dashboard/overview?timeframe=1d` returns current totals for requests, tokens, and estimated API cost plus comparison data with `canCompare: true`
- **AND** the previous-window totals are lower than the current-window totals
- **THEN** the dashboard renders percentage-change indicators on the `Requests`, `Tokens`, and `Est. API Cost` cards
- **AND** each increase uses an upward indicator with positive `emerald` styling

#### Scenario: Weekly overview renders decrease from previous window

- **WHEN** `GET /api/dashboard/overview?timeframe=7d` returns comparison data with `canCompare: true`
- **AND** at least one of the previous-window totals for requests, tokens, or estimated API cost is higher than the current-window total for that same card
- **THEN** the dashboard renders a downward percentage-change indicator for that card
- **AND** that decrease uses negative `red` styling

#### Scenario: Partial previous window suppresses comparison

- **WHEN** `GET /api/dashboard/overview?timeframe=7d` or `GET /api/dashboard/overview?timeframe=30d` cannot prove the immediately preceding same-length window is fully covered by eligible request-log history
- **THEN** the overview response marks the comparison as unavailable
- **AND** the dashboard does not render percentage-change indicators on the `Requests`, `Tokens`, or `Est. API Cost` cards

#### Scenario: Non-comparison cards remain unchanged

- **WHEN** the dashboard renders overview cards from `GET /api/dashboard/overview` with or without comparison data
- **THEN** `Error rate` and `Account burn projection` do not render previous-window percentage-change indicators

### Requirement: Dashboard estimated cost card meta avoids duplicate estimate and cache copy

The dashboard overview `Est. API Cost` summary card SHALL render its meta text as only the averaged cost for the selected overview timeframe. The meta text MUST NOT append duplicate estimate wording or cached-token counts.

#### Scenario: Weekly estimated cost card shows only average-per-day text

- **WHEN** `GET /api/dashboard/overview?timeframe=7d` returns an `Est. API Cost` total and the summary metrics also include cached input tokens
- **THEN** the dashboard renders the cost-card meta text as `Avg/day <currency value>`
- **AND** the same meta text does not include `API estimate`
- **AND** the same meta text does not include `cached`

#### Scenario: Daily estimated cost card shows only average-per-hour text

- **WHEN** `GET /api/dashboard/overview?timeframe=1d` returns an `Est. API Cost` total
- **THEN** the dashboard renders the cost-card meta text as `Avg/hr <currency value>`
- **AND** the same meta text does not include any extra suffix text

### Requirement: Upstream proxy admin creation flows use modal dialogs

The Settings upstream proxy section SHALL present endpoint creation, pool creation, and
pool-member addition as modal dialogs opened from explicit trigger buttons. The creation form
fields (endpoint name/scheme/host/port/credentials, pool name/member selection, pool-member
pool/endpoint selectors) SHALL NOT be rendered in the always-visible Settings layout; they
SHALL only mount when their dialog is open. Submitting a creation dialog SHALL call the existing
upstream proxy admin mutation, refresh the displayed admin state, and close the dialog on success;
a failed submission SHALL keep the dialog open so the operator can retry.

#### Scenario: Creation forms are hidden until a dialog opens

- **WHEN** an operator views the Settings page upstream proxy section
- **THEN** no endpoint, pool, or pool-member creation input fields are present in the document
- **AND** the section shows trigger buttons for adding an endpoint, creating a pool, and adding a pool member

#### Scenario: Operator creates a pool from a dialog

- **GIVEN** the upstream proxy admin API returns at least one endpoint
- **WHEN** an operator opens the create-pool dialog, names the pool, selects endpoint members, and submits
- **THEN** the dashboard calls the pool creation API with the selected endpoint ids
- **AND** refreshes the displayed upstream proxy admin state
- **AND** closes the dialog

#### Scenario: Failed creation keeps the dialog open

- **WHEN** a creation dialog submission rejects with an error
- **THEN** the dialog remains open
- **AND** the entered values are preserved so the operator can retry

### Requirement: Upstream proxy admin section summarizes configured endpoints and pools

The always-visible Settings upstream proxy section SHALL render a summary/management view that
shows the routing-enabled toggle, the default-pool selector, and readable lists of the configured
endpoints and pools (including each pool's active state and endpoint count). When no endpoints or
no pools are configured, the section SHALL show an explicit empty state for that list rather than
a blank region.

#### Scenario: Configured endpoints and pools are listed

- **WHEN** the upstream proxy admin state includes endpoints and pools
- **THEN** the section lists each endpoint with its scheme, host, and port
- **AND** lists each pool with its active state and endpoint count

#### Scenario: Empty proxy configuration shows an empty state

- **WHEN** the upstream proxy admin state has no endpoints and no pools
- **THEN** the section shows an explicit empty-state message for endpoints and for pools

### Requirement: Account routing and proxy-binding controls size predictably

The account detail routing-policy selector and the account proxy-pool selector SHALL size
themselves responsively within their container instead of using an arbitrary fixed pixel width,
and SHALL truncate long option labels gracefully rather than overflowing their container or
collapsing below a usable minimum width.

#### Scenario: Routing-policy select fills its control row

- **WHEN** the account detail panel renders the routing-policy selector
- **THEN** the selector trigger constrains its width to its container with a usable minimum
- **AND** does not hardcode a fixed `w-44` width

#### Scenario: Long proxy-pool name is truncated

- **WHEN** the account proxy-pool selector renders a pool whose name is longer than the trigger width
- **THEN** the selected label is truncated with an ellipsis within the trigger
- **AND** the selector does not overflow its container

### Requirement: Account proxy binding can test the selected pool

The account detail proxy-binding panel SHALL expose an in-place test action for the selected proxy
pool when that pool has at least one endpoint. Activating the action SHALL call the existing upstream
proxy endpoint-test API for the selected pool's first endpoint and SHALL display the latest bounded
reachability result without showing proxy credentials or account tokens.

#### Scenario: Operator tests the selected account proxy pool

- **GIVEN** an account proxy binding panel has a selected pool with at least one endpoint
- **WHEN** an operator activates the pool test action
- **THEN** the dashboard calls the existing endpoint-test API with the selected pool's first endpoint id
- **AND** displays whether the endpoint was reachable, plus bounded status/latency details when provided

#### Scenario: Pool test is disabled when no endpoint is available

- **WHEN** the selected account proxy pool has no endpoints
- **THEN** the pool test action is disabled

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

### Requirement: Account alias is edited inline from the detail header

The account detail header SHALL display the account's local label (the alias when set, otherwise the
display name or email) next to an edit (pencil) control, and SHALL NOT render a separate always-visible
alias form. Activating the edit control SHALL replace the label with an inline text input pre-filled
with the current alias plus confirm and cancel controls. Confirming SHALL persist the alias via the
existing alias handler (an empty value clears the alias) and return to the display state; cancelling
SHALL discard the edit without a network call. When an alias is set, the header SHALL still surface the
account email as a subtitle so the underlying account remains identifiable.

#### Scenario: Pencil reveals the inline alias editor

- **WHEN** an operator views the account detail header
- **THEN** the account local label is shown next to an "Edit alias" control
- **AND** no separate "Account alias" form card is rendered
- **WHEN** the operator activates the "Edit alias" control
- **THEN** the label is replaced by a text input pre-filled with the current alias, with save and cancel controls

#### Scenario: Saving and clearing the alias inline

- **GIVEN** the inline alias editor is open
- **WHEN** the operator enters a label and confirms
- **THEN** the alias is persisted via the existing alias handler and the header returns to the display state
- **WHEN** the operator clears the input and confirms
- **THEN** the alias is cleared via the existing alias handler

#### Scenario: Cancelling discards the edit

- **GIVEN** the inline alias editor is open with unsaved changes
- **WHEN** the operator cancels
- **THEN** the editor closes without calling the alias handler
- **AND** the displayed label is unchanged

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

### Requirement: Daily Breakdown CSV export stays chronological

The dashboard SHALL export `/reports` `Daily Breakdown` CSV rows in ascending `Day` order regardless of the current visible table sort key or direction.

#### Scenario: CSV export ignores visible descending day sort

- **WHEN** an authenticated operator exports the `Daily Breakdown` CSV while the visible table is sorted newest-first
- **THEN** the CSV rows are written from the earliest day to the latest day

#### Scenario: CSV export ignores non-day visible sort

- **WHEN** an authenticated operator exports the `Daily Breakdown` CSV while the visible table is sorted by another column
- **THEN** the CSV rows are still written from the earliest day to the latest day

### Requirement: Daily Breakdown sortable headers show visible sort state

The dashboard SHALL render a visible sort icon on every sortable `/reports` `Daily Breakdown` header. Inactive sortable headers SHALL show a muted gray unsorted indicator, and the active sorted header SHALL show a bright directional indicator matching the current ascending or descending sort direction.

#### Scenario: Inactive sortable headers show unsorted indicator

- **WHEN** an authenticated operator views `/reports`
- **THEN** each sortable `Daily Breakdown` header shows a visible unsorted icon when that column is not the active sort column

#### Scenario: Active sortable header shows ascending indicator

- **WHEN** an authenticated operator activates a `Daily Breakdown` header and the table sort is ascending for that column
- **THEN** that header shows the active ascending sort icon instead of the muted unsorted icon

#### Scenario: Active sortable header shows descending indicator

- **WHEN** an authenticated operator activates the same `Daily Breakdown` header again and the table sort becomes descending
- **THEN** that header shows the active descending sort icon instead of the muted unsorted icon

### Requirement: Dashboard supports runtime locale selection

The dashboard SHALL load translations through `i18next` + `react-i18next`, support at least `en` (default) and `zh-CN` locales, persist the user's selection in `localStorage` under the key `codex-lb-language`, and apply the active locale to the document's `lang` attribute. When no persisted preference exists, the dashboard SHALL detect the browser language and use `zh-CN` for any `zh*` tag and `en` otherwise.

#### Scenario: First visit with a Chinese browser

- **WHEN** a user opens the dashboard for the first time with `navigator.language = "zh-CN"` and no persisted preference
- **THEN** the in-scope surface (header, status-bar labels, auth screens) renders in Simplified Chinese
- **AND** `localStorage` contains `codex-lb-language=zh-CN`

#### Scenario: First visit with an unsupported browser language

- **WHEN** a user opens the dashboard for the first time with `navigator.language` set to anything that does not start with `zh`
- **THEN** the in-scope surface renders in English
- **AND** the dashboard does not raise locale-loading errors

#### Scenario: User toggles the language

- **WHEN** the user activates the language switcher in the app header and selects `简体中文`
- **THEN** the in-scope surface re-renders in Simplified Chinese without a full page reload
- **AND** `localStorage.codex-lb-language` is set to `zh-CN`
- **AND** `document.documentElement.lang` is set to `zh-CN`

#### Scenario: Selection persists across reloads

- **WHEN** the user reloads the dashboard after selecting a language
- **THEN** the previously selected language is reapplied before the first paint

### Requirement: Settings page renders in the active locale

The Settings page and its constituent sections (`Appearance`, `Routing`, `Import`, `Session`, `Password`, `TOTP`) SHALL render all user-visible strings — page title and subtitle, section headings and descriptions, switch and select labels, button labels, dialog titles and descriptions, validation messages, warning banners, and toast messages — through the active i18n locale. Selecting `zh-CN` MUST translate the entire surface above to Simplified Chinese, with the explicit exceptions of the embedded `ApiKeysSection`, `FirewallSection`, `QuotaPlannerSection`, `StickySessionsSection`, and `UpstreamProxySettings` rendered inside Settings, which belong to other capabilities and remain English until their own migrations.

#### Scenario: Switching to Simplified Chinese translates the Settings page

- **WHEN** a user opens the Settings page with `zh-CN` selected as the active language
- **THEN** the page heading reads `设置`
- **AND** every section heading inside the page (`外观`, `路由`, `导入`, `会话`, `密码`, `TOTP`) renders in Simplified Chinese
- **AND** every dialog opened from the page (`Set password`, `Change password`, `Remove password`, `Verify password`, `Enable TOTP`, `Disable TOTP`) renders its title, description, field labels, and submit button in Simplified Chinese

#### Scenario: Session lifetime invalid-input warning preserves the inline example

- **WHEN** a user enters a non-integer hour value such as `1.5` into the dashboard session lifetime input
- **THEN** the inline warning renders with `1.5` wrapped in `<code>` regardless of the active locale
- **AND** the surrounding sentence is translated according to the active locale

#### Scenario: TOTP code-length validation respects the active locale

- **WHEN** a user submits the Enable TOTP or Disable TOTP form with a code shorter than 6 characters and the active locale is `zh-CN`
- **THEN** the form-level validation message renders as `请输入 6 位验证码`
- **AND** the same submission with `en` active renders as `Enter a 6-digit code`

### Requirement: Dashboard request details expose client IP

The dashboard request-log API response MUST expose the persisted `clientIp` value when present. The Request Details dialog MUST render `Client IP` with the full value when present, MUST allow copying the value, and MUST render `—` when no client IP is stored.

#### Scenario: Request details show client IP

- **WHEN** a request log entry has `clientIp: "203.0.113.7"`
- **THEN** the Request Details dialog renders `Client IP` with value `203.0.113.7`
- **AND** the value can be copied

#### Scenario: Request details show missing client IP

- **WHEN** a request log entry has `clientIp: null`
- **THEN** the Request Details dialog renders `Client IP` with value `—`

### Requirement: Request details expose conversation filtering

The request-details dialog MUST render Client IP and Conversation ID in one
shared row. When present, the conversation ID MUST be a clickable semantic text
control without an underline. Activating it MUST close the dialog, preserve all
existing request-log filters, set the clicked conversation ID as the active
URL-backed conversation filter, and reset pagination.

#### Scenario: Clicking a conversation filters the request log
- **GIVEN** request details display conversation ID `conv-a` while other filters
  are active
- **WHEN** the conversation ID is activated
- **THEN** the dialog closes
- **AND** the other filters remain active
- **AND** the active URL-backed conversation filter becomes `conv-a`
- **AND** pagination resets

### Requirement: Request details link to conversation details

For users with `conversations:read`, request details with a conversation ID MUST
offer a separate View details action beside that ID. Activating it MUST close
request details and open the existing Conversation Details dialog for the exact
opaque conversation ID without changing request-log filters or pagination.
Existing conversation-ID filtering and copying MUST remain unchanged. Without
a conversation ID or the permission, the action MUST be absent. Conversation
details MUST NOT be fetched before activation. Closing the conversation dialog
MUST clear its selection. Loading and errors MUST use the existing dialog behavior.

#### Scenario: Opening conversation details directly
- **GIVEN** an authorized user views request details for conversation `conv / a`
- **WHEN** they activate View details
- **THEN** request details close and Conversation Details open for `conv / a`
- **AND** existing filters and pagination remain unchanged

#### Scenario: Unavailable conversation action
- **GIVEN** a request has no conversation ID or the user lacks `conversations:read`
- **WHEN** request details open
- **THEN** no conversation-details action or fetch occurs

#### Scenario: Fetch only on selection
- **GIVEN** request details display a conversation ID
- **WHEN** the user has not activated View details
- **THEN** no conversation-details fetch occurs
- **WHEN** they open, close, and select another conversation
- **THEN** the dialog displays the newly selected conversation

### Requirement: Dashboard and report metrics count distinct conversations

Dashboard overview metrics MUST include a Conversations card between Est. API
Cost and Error Rate, counting distinct non-empty conversation IDs in the
selected timeframe. Report summary metrics MUST include a Conversations card
immediately after Requests, counting distinct non-empty IDs across the complete
filtered report range. A conversation spanning multiple days MUST count once in
each applicable daily row and once in the report-wide total. Neither card MUST
render a `{count} distinct` secondary label.

#### Scenario: Dashboard count deduplicates IDs
- **GIVEN** the selected dashboard timeframe contains repeated, null, and empty
  conversation IDs
- **WHEN** overview metrics are rendered
- **THEN** the Conversations card counts each distinct non-empty ID once
- **AND** the card is between Est. API Cost and Error Rate

#### Scenario: Report summary and daily counts use distinct IDs
- **GIVEN** one conversation has requests on two report days and another has
  requests on one day
- **WHEN** report metrics are rendered
- **THEN** the summary counts two distinct conversations overall
- **AND** each applicable daily row counts the spanning conversation once
- **AND** the Conversations summary card is immediately after Requests

### Requirement: Dashboard conversation trends are bucketed distinctly

The dashboard overview response MUST expose `trends.conversations` with one
point for each configured timeframe bucket. Each point MUST count distinct,
non-empty conversation IDs within that bucket, and a conversation repeated
across models or service tiers in one bucket MUST count once. Missing buckets
MUST be zero. The Conversations card MUST use this series, while its summary
total MUST remain the exact timeframe aggregate rather than a sum of trend
points.

#### Scenario: Conversation trend de-duplicates model groups
- **GIVEN** one bucket contains the same conversation ID under two models and a
  second distinct conversation ID under one model
- **WHEN** the dashboard overview trends are rendered
- **THEN** the populated bucket's conversation point is `2`
- **AND** the series contains one point per configured bucket

#### Scenario: Empty conversation buckets are zero-filled
- **GIVEN** the selected dashboard timeframe has no valid conversation IDs in
  one or more buckets
- **WHEN** the dashboard overview response is built
- **THEN** each empty bucket's conversation point is `0`

### Requirement: Report conversation columns sort and export

The daily report table MUST place a Conversations column between Reqs and Input
Tokens. The column MUST support numeric sorting and CSV export, and its values
MUST preserve the distinct non-empty daily conversation counts, including
zero-filled days.

#### Scenario: Daily conversation values are sortable and exported
- **GIVEN** daily report rows have different conversation counts, including a
  zero-count row
- **WHEN** the Conversations column is sorted or CSV export is generated
- **THEN** sorting is numeric by conversation count
- **AND** the column appears between Reqs and Input Tokens
- **AND** CSV output contains the Conversations header and each row's value

### Requirement: Account usage panel supports confirmed usage reset

The Accounts page selected-account Usage panel SHALL expose a Reset action
inside the Usage resets row when reset-credit availability is shown. The action
SHALL require operator confirmation, SHALL consume one upstream usage reset
credit for the selected account, SHALL force-fetch upstream usage after a
successful or idempotently successful consume without sending model probe
traffic, and SHALL refresh account-related dashboard queries after success. The
dashboard SHALL NOT reduce or add permanent polling intervals to make this
reset appear sooner. When the selected account summary exposes
`reset_credit_nearest_expires_at`, the Usage resets row SHALL show the earliest
reset-credit expiry using the dashboard's local datetime formatting and a
compact remaining-time label.

#### Scenario: Confirmed account usage reset consumes one credit
- **GIVEN** an active selected account is visible on the Accounts page
- **AND** the selected account has at least one available usage reset credit
- **WHEN** the operator clicks the Usage panel Reset action
- **AND** confirms the dialog
- **THEN** the dashboard sends a usage reset consume request for the selected account
- **AND** codex-lb does not send a model probe request
- **AND** account-related usage, trend, reset-credit, and dashboard summary
  queries are invalidated after success
- **AND** no reset-credit availability query is configured with a permanent
  refetch interval

#### Scenario: Dismissed account usage reset does not consume a credit
- **GIVEN** an active selected account is visible on the Accounts page
- **WHEN** the operator clicks the Usage panel Reset action
- **AND** cancels the dialog
- **THEN** the dashboard does not send a usage reset consume request

#### Scenario: Usage reset row shows nearest reset-credit expiry
- **GIVEN** an active selected account is visible on the Accounts page
- **AND** the selected account summary exposes `reset_credit_nearest_expires_at`
- **WHEN** the Usage panel renders the Usage resets row
- **THEN** the row shows the earliest reset-credit expiry in local time
- **AND** the row shows a compact remaining-time label for that expiry

### Requirement: Automations page supports job lifecycle actions

The `Automations` page MUST let operators create, edit, enable/disable, delete, and run jobs, including selecting accounts and model.

#### Scenario: Create job in GUI

- **WHEN** a user creates a daily ping automation with schedule, model, and account set
- **THEN** the SPA submits `POST /api/automations`
- **AND** the new job appears in the jobs table with `nextRunAt`

#### Scenario: Toggle enablement

- **WHEN** a user toggles a job off or on from the jobs table
- **THEN** the SPA submits `PATCH /api/automations/{id}`
- **AND** the table reflects the updated enabled state

#### Scenario: Trigger manual run

- **WHEN** a user selects `Run now` for a job
- **THEN** the SPA submits `POST /api/automations/{id}/run-now`
- **AND** latest run status updates in the jobs table

### Requirement: Automations page surfaces run failures

The UI MUST present recent run outcomes and show failure details to the user.

#### Scenario: Inspect failed run

- **WHEN** a user opens run history for a job with a failed run
- **THEN** the UI shows run status, timestamps, and failure details (`errorCode`, `errorMessage`)
- **AND** the jobs table highlights the latest failed state

### Requirement: Automations form validates required scheduling inputs

The Automations create/edit form MUST prevent submission when required fields are missing or invalid.

#### Scenario: All-accounts selection is allowed

- **WHEN** a user leaves `accountIds` empty in the create/edit form
- **THEN** the SPA treats the selection as `All accounts`
- **AND** submit remains allowed when other required fields are valid

#### Scenario: Block submit when there are no available accounts

- **WHEN** the accounts catalog is empty
- **THEN** the SPA blocks submit and shows a validation message

#### Scenario: Block submit when schedule time or timezone is invalid

- **WHEN** a user provides an invalid schedule time or timezone value
- **THEN** the SPA blocks submit and shows a validation message

### Requirement: Automations page accepts extended reasoning efforts

The Automations page SHALL allow operators to create and update scheduled
refresh jobs using any reasoning effort advertised by the selected model,
including extended GPT-5.6 efforts such as `max` and `ultra`.

#### Scenario: Automation dialog offers extended model reasoning efforts

- **WHEN** a selected model advertises `max` or `ultra` in `supportedReasoningEfforts`
- **THEN** the automation create/edit dialog offers those efforts as selectable values

### Requirement: Account management page supports account import and OAuth add flows

The Accounts page SHALL support account import, untargeted OAuth account
addition, and targeted OAuth reauthentication. Reauthentication MUST preserve
separate local seats that share one workspace `chatgpt_account_id`.

#### Scenario: Account import

- **WHEN** a user opens the import flow and uploads an auth.json file
- **THEN** the app calls `POST /api/accounts/import` and refreshes the account list on success

#### Scenario: OAuth add account

- **WHEN** a user clicks the add account button
- **THEN** an OAuth dialog opens with browser and device code flow options
- **AND** the OAuth start request does not target an existing local account

#### Scenario: Reauthentication targets the selected local seat

- **GIVEN** two local Team seats share one upstream `chatgpt_account_id`
- **AND** each seat has a distinct `chatgpt_user_id`
- **WHEN** an operator starts reauthentication from one selected account row
- **THEN** the selected local account ID is retained in server-side OAuth flow state
- **AND** successful OAuth replaces credentials only on that selected row

#### Scenario: Wrong browser seat is rejected

- **GIVEN** reauthentication targets seat A
- **WHEN** OAuth returns seat B from the same Team workspace
- **THEN** the flow fails without writing seat B's credentials to seat A
- **AND** neither local account row is merged or deleted

#### Scenario: Token refresh preserves seat identity

- **WHEN** a refresh response contains a stable user principal
- **THEN** the service persists that principal as `chatgpt_user_id`
- **AND** continues using `chatgpt_account_id` as the upstream workspace identity

### Requirement: Dashboard tolerates browser translation DOM mutation

The dashboard HTML shell SHALL allow browser/extension translation while protecting React reconciliation from external DOM node moves.

#### Scenario: Dashboard permits browser translation

- **WHEN** the browser loads the dashboard HTML shell
- **THEN** the document, body, and React root do not opt out of browser translation

#### Scenario: Dashboard tolerates externally moved React nodes

- **WHEN** an extension moves a React-owned DOM node before React removes or inserts around it
- **THEN** the dashboard startup guard logs the external mutation
- **AND** the guarded DOM operation returns without throwing a reconciliation-stopping exception

### Requirement: Reports page sends browser-local timezone context

The `/reports` page SHALL detect the browser's current IANA timezone, cache the latest detected valid value locally for convenience, and include a valid timezone in `GET /api/reports` requests whenever one is available. The page SHALL prefer the browser's current valid timezone over any cached value, SHALL reuse the cached valid timezone when live detection is unavailable or invalid, and SHALL omit the `timezone` query parameter only when neither the live nor cached value is valid.

#### Scenario: Reports page includes browser timezone on requests

- **WHEN** an authenticated operator opens `/reports` or changes a report filter
- **THEN** the request to `GET /api/reports` includes the browser's current IANA timezone in the `timezone` query parameter when detection succeeds

#### Scenario: Reports page reuses cached timezone when live detection fails

- **WHEN** the browser cannot provide a valid IANA timezone name
- **AND** the page has a cached valid timezone from an earlier successful detection
- **THEN** the reports page still requests `GET /api/reports`
- **AND** the request uses the cached valid timezone in the `timezone` query parameter

#### Scenario: Reports page omits timezone only when no valid timezone is available

- **WHEN** the browser cannot provide a valid IANA timezone name
- **AND** the page does not have a cached valid timezone
- **THEN** the reports page still requests `GET /api/reports`
- **AND** the request omits the `timezone` query parameter

### Requirement: Reports endpoint applies timezone-aware ranges and daily bucketing

`GET /api/reports` SHALL interpret `start_date` and `end_date` as calendar dates in the supplied IANA timezone, convert those local-midnight boundaries to UTC for filtering, and group `daily` rows by calendar day in that same timezone. When the timezone is missing or invalid, the endpoint MUST fall back to UTC.

#### Scenario: Reports endpoint uses local-day buckets before UTC midnight

- **WHEN** `/api/reports` receives `start_date`, `end_date`, and `timezone=America/Los_Angeles`
- **AND** a request log row falls on `2026-06-02T01:30:00Z`
- **THEN** the row is included in the `2026-06-01` daily bucket for that response

#### Scenario: Reports endpoint falls back to UTC for invalid timezone

- **WHEN** `/api/reports` receives an invalid `timezone` value
- **THEN** the endpoint still returns a successful response
- **AND** it interprets the report range and daily buckets in UTC

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

### Requirement: API keys settings expose quota privacy toggle
The Settings page SHALL include a toggle in the API Keys section that controls `hide_upstream_quota_from_api_keys`.

#### Scenario: Toggle is visible with the API keys controls

- **WHEN** the Settings page renders the API Keys section
- **THEN** the quota privacy toggle SHALL be shown alongside the API key auth toggle

#### Scenario: Toggle persists through settings save

- **WHEN** the user changes the quota privacy toggle
- **THEN** the settings update request SHALL include `hideUpstreamQuotaFromApiKeys`

### Requirement: Dashboard request-log archive lookup
The dashboard request-log detail dialog SHALL use each row's `archiveRequestId` for conversation archive lookup when that field is present. For older API responses that omit `archiveRequestId`, it SHALL fall back to the row's `requestId`.

#### Scenario: Detail dialog uses archive lookup id
- **WHEN** a request-log row has `requestId: "resp_123"` and `archiveRequestId: "req_123"`
- **AND** the operator opens the request detail dialog
- **THEN** the archive panel queries archive records for `req_123`

#### Scenario: Detail dialog remains backward compatible
- **WHEN** a request-log row does not include `archiveRequestId`
- **AND** the operator opens the request detail dialog
- **THEN** the archive panel queries archive records for the row's `requestId`

### Requirement: Dashboard manages OpenAI-compatible model sources

The Settings page SHALL provide an operator control surface for
OpenAI-compatible model sources. Operators SHALL be able to create a source with
a name, base URL, optional upstream API key, route-shape support flags, and one
or more model ids. Operators SHALL be able to enable, disable, and delete
sources. The dashboard MUST NOT expose decrypted upstream source API keys after
creation.

#### Scenario: Operator creates a vLLM model source

- **WHEN** an operator submits a model source with base URL `http://localhost:8000/v1`
- **AND** model id `local-coder`
- **THEN** the dashboard calls `POST /api/model-sources/`
- **AND** the new source appears in the Settings model-source list

#### Scenario: Operator disables a model source

- **WHEN** an operator toggles an enabled model source off
- **THEN** the dashboard calls `PATCH /api/model-sources/{sourceId}` with `isEnabled=false`
- **AND** the source remains listed as disabled

### Requirement: Dashboard model picker includes source models

The dashboard model listing endpoint (`GET /api/models`) SHALL include enabled
OpenAI-compatible source models alongside subscription registry models so
API-key model allowlists can reference source models. Duplicate slugs MUST be
listed once with the subscription entry taking precedence.

#### Scenario: Allowed-models picker offers a source model

- **GIVEN** an enabled OpenAI-compatible source exposes model `local-coder`
- **WHEN** the dashboard requests `GET /api/models`
- **THEN** the response includes `local-coder`
- **AND** an API key allowlisted to `local-coder` can call it through the proxy

### Requirement: Dashboard API-key forms assign model sources

The API-key create dialog and a key's Settings tab SHALL allow operators to assign zero or more model sources
separately from account assignments. Selecting no model sources SHALL mean all eligible sources are allowed subject to
model allowlists and route compatibility. When a source-scoped key's assigned sources were all deleted, the Settings
tab SHALL explain the missing restriction and SHALL send an empty source list only when the operator explicitly
removes the restriction.

#### Scenario: Create key scoped to a model source

- **WHEN** an operator creates an API key and selects model source `src_vllm`
- **THEN** the dashboard sends `assignedSourceIds=["src_vllm"]`
- **AND** the API key response preserves the assigned source id

#### Scenario: Edit key clears source scope

- **WHEN** an API key has assigned source ids
- **AND** an operator clears the source selection in the key's Settings tab and saves
- **THEN** the dashboard sends `assignedSourceIds=[]`

#### Scenario: Deleted sources keep the key denied

- **WHEN** a source-scoped key has no remaining assigned sources
- **AND** the operator saves its Settings tab without removing the restriction
- **THEN** the dashboard does not send `assignedSourceIds`

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

### Requirement: Accounts page can sort by available reset credits

The Accounts page sort selector SHALL offer a "Most reset credits" option and SHALL use it as the default Accounts page ordering. That ordering SHALL sort accounts by `available_reset_credits` descending. Ties SHALL be broken by `reset_credit_nearest_expires_at` ascending (soonest expiring first), and accounts with no expiry SHALL sort after accounts that have one.

#### Scenario: More available credits sorts first
- **WHEN** the operator opens the Accounts page with the default sort mode
- **AND** account A has `available_reset_credits: 4` and account B has `available_reset_credits: 1`
- **THEN** account A appears before account B

#### Scenario: Tie breaks by soonest expiry
- **WHEN** two accounts have equal `available_reset_credits`
- **AND** one account's soonest credit expires before the other's
- **THEN** the account with the earlier `reset_credit_nearest_expires_at` appears first

### Requirement: Dashboard accounts section exposes a reset-credits redeem action

The Dashboard Accounts section SHALL render a reset action next to the existing Details action in both the table and grid views for any account with `available_reset_credits > 0`. The grid view label SHALL read `Reset (N)`. The table view MAY remain icon-only, but its tooltip/title SHALL include the available reset-credit count. The action SHALL be absent when `available_reset_credits` is `0`. Activating the action SHALL open the same confirmation flow as the Accounts page reset action.

#### Scenario: Table view shows reset next to details
- **WHEN** the Dashboard Accounts section renders in table view for an account with `available_reset_credits > 0`
- **THEN** a "Reset" action appears in the same action cell as the Details action

#### Scenario: Grid view shows reset next to details
- **WHEN** the Dashboard Accounts section renders in grid view for an account with `available_reset_credits > 0`
- **THEN** a `Reset (N)` button appears next to the Details button on the account card

#### Scenario: Reset action absent when no credits
- **WHEN** an account reports `available_reset_credits: 0`
- **THEN** the Dashboard Accounts section renders no "Reset" action for that account in either view

### Requirement: Dashboard header shows the total available reset-credit count

The dashboard top navigation SHALL render the total available reset-credit count on the Accounts tab, pinned to the tab's upper-right radius. The total SHALL equal the sum of `available_reset_credits` across the current account list data. The badge SHALL display `99+` when the total exceeds 99 and SHALL be hidden when the total is 0. The badge SHALL also be hidden when dashboard setting `show_reset_credit_badges` is disabled.

#### Scenario: Accounts tab shows the summed total
- **WHEN** the current account list totals `available_reset_credits` to `14`
- **THEN** the Accounts nav tab displays a badge with `14`

#### Scenario: Accounts tab caps large totals
- **WHEN** the current account list totals `available_reset_credits` to `120`
- **THEN** the Accounts nav tab displays a badge with `99+`

#### Scenario: Accounts tab hides empty totals
- **WHEN** every account reports `available_reset_credits: 0`
- **THEN** the Accounts nav tab displays no reset-credit badge

#### Scenario: Top navigation reset-credit badge visibility follows settings

- **GIVEN** the settings API returns `show_reset_credit_badges: false`
- **AND** account summaries report available reset credits
- **WHEN** the top navigation renders
- **THEN** the Accounts navigation reset-credit badge is absent

### Requirement: Reset actions display a single-unit expiry countdown

Every "Reset" button SHALL display a small countdown label of the soonest-expiring credit's expiry, formatted as a single time unit: `"${d}d"` for any remaining duration of one day or more, `"${h}h"` for durations under one day but at least one hour, `"${m}m"` for durations under one hour but at least one minute, and `"now"` for durations under one minute. The label SHALL render in the destructive/red color when the remaining duration is strictly less than 7 days, and in the default muted color otherwise.

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
- **THEN** the countdown label reads `13h`
- **AND** the label uses the destructive/red color

#### Scenario: Sub-minute duration shows now
- **WHEN** a Reset button renders for a credit whose `expires_at` is 30 seconds away
- **THEN** the countdown label reads `now`
- **AND** the label uses the destructive/red color

### Requirement: Reports API SHALL reject oversized daily ranges

`GET /api/reports` SHALL reject requests whose inclusive `start_date` to
`end_date` span exceeds 730 calendar days after applying endpoint defaults for
any omitted bound.

#### Scenario: Oversized report range is rejected

- **WHEN** an authenticated operator requests `/api/reports` with a date span
  longer than 730 days
- **THEN** the API returns a 400-class response
- **AND** the backend does not expand the request into per-day report buckets

#### Scenario: Single-bound report range is validated after defaults

- **WHEN** an authenticated operator requests `/api/reports` with only
  `start_date` set to a date more than 730 days before the effective end date
- **THEN** the API returns a 400-class response
- **AND** the backend does not expand the request into per-day report buckets

### Requirement: Request detail dialog displays elapsed latency
The dashboard request-log `View Details` dialog SHALL display `latency_ms` as an `Elapsed` field next to the `Plan` field. The display value SHALL use `ms` units for values under 1000 ms and `s` units (to one decimal) for values 1000 ms or greater. When `latency_ms` is null, the field SHALL render an em dash (`—`).

#### Scenario: Latency under one second shown in ms
- **WHEN** a request log detail dialog opens and the row has `latency_ms: 500`
- **THEN** the dialog displays `500 ms` in the `Elapsed` field

#### Scenario: Latency at or above one second shown in seconds
- **WHEN** a request log detail dialog opens and the row has `latency_ms: 1500`
- **THEN** the dialog displays `1.5 s` in the `Elapsed` field

#### Scenario: Missing latency renders em dash
- **WHEN** a request log detail dialog opens and the row has `latency_ms: null`
- **THEN** the dialog displays `—` in the `Elapsed` field

### Requirement: Dashboard serving is compressed, cache-correct, and chart-lazy

Dashboard API and static-asset responses MUST be served gzip-compressed when the client accepts it, while proxy paths MUST NOT pass through a compressing wrapper. Content-hashed assets under `/assets/` MUST be served with immutable year-long `Cache-Control`; `index.html` MUST remain `no-cache`. Chart vendor code MUST NOT load before first paint: it MUST live in an async-only chunk that is neither statically imported by the entry chunk nor modulepreloaded. Static assets MUST be served with their correct web MIME types (`.js`/`.mjs` as `text/javascript`, `.css` as `text/css`, `.svg` as `image/svg+xml`, `.json` as `application/json`, `.woff`/`.woff2` as `font/woff`/`font/woff2`, `.html` as `text/html`) regardless of the host operating system's `mimetypes` registry state, so strict browser MIME checking never rejects dashboard module scripts.

#### Scenario: Assets are compressed and immutable

- **WHEN** a browser requests a hashed asset under `/assets/` with `Accept-Encoding: gzip`
- **THEN** the response is gzip-encoded
- **AND** carries `Cache-Control: public, max-age=31536000, immutable`

#### Scenario: index.html stays fresh across deploys

- **WHEN** the SPA shell is requested
- **THEN** the response carries `Cache-Control: no-cache`

#### Scenario: Proxy streaming paths are never compressed by the dashboard wrapper

- **WHEN** a request targets a proxy path (`/backend-api/*`, `/v1/*`)
- **THEN** the dashboard gzip middleware passes it through untouched

#### Scenario: Ranged asset requests bypass compression

- **WHEN** an asset request carries a `Range` header
- **THEN** the response is served uncompressed with a valid 206 `Content-Range` over unencoded bytes

#### Scenario: Chart vendor code loads lazily

- **WHEN** the built dashboard entry page loads
- **THEN** the recharts chunk is not statically imported by the entry chunk and not modulepreloaded
- **AND** charts render correctly once their async chunk loads

#### Scenario: Module scripts survive a poisoned OS MIME registry

- **GIVEN** the host operating system maps `.js` to `text/plain` in its `mimetypes` sources (e.g. Windows `HKCR` registry entries)
- **WHEN** a browser requests a hashed `.js` asset under `/assets/`
- **THEN** the response `Content-Type` is `text/javascript`
- **AND** the dashboard SPA boots instead of failing strict module MIME checking

### Requirement: Account quota displays hide expired windows

Account summary payloads SHALL present the primary (short) quota window as absent — null remaining percentage, remaining credits, reset timestamp, and window duration — when its last usage sample has an elapsed `reset_at`, instead of freezing the stale sample. Accounts without any primary sample SHALL NOT display an optimistic 100% primary remaining default. Long (weekly/monthly) window displays keep the raw samples: their consumers advance elapsed resets by design (weekly credit pace) and upstream still reports them, so staleness is transient. Displayed account status SHALL apply the same expired-window treatment routing applies before deriving the badge: an elapsed primary sample is a reset window, not exhaustion evidence, so a frozen ≥100% sample MUST NOT surface a rate-limited badge that the selector would never apply.

#### Scenario: Expired 5h sample displays as absent

- **GIVEN** upstream stopped reporting the short window and an account's last primary sample has an elapsed `reset_at`
- **WHEN** the dashboard loads account summaries
- **THEN** the account's primary window fields are null
- **AND** the UI renders the 5h quota as absent, matching the weekly-only presentation

#### Scenario: Expired exhausted sample does not display rate-limited

- **GIVEN** an active account whose last primary sample reports 100% used with an elapsed `reset_at`
- **WHEN** account summaries are built
- **THEN** the primary window fields are null
- **AND** the account status stays active instead of inferring rate-limited from the stale sample

#### Scenario: Missing primary data is not optimistic

- **WHEN** an account has no primary usage sample and is not a weekly-only plan
- **THEN** `primary_remaining_percent` is null rather than 100

#### Scenario: Live windows are unaffected

- **WHEN** an account's primary sample has an unexpired `reset_at`
- **THEN** the summary displays its used/remaining percentages, reset, and duration unchanged

### Requirement: Logs page hides the Conversations view without conversation access

The Logs page view toggle MUST render the Conversations option only for a
principal with `conversations:read`. For any other principal, the effective
view MUST be Request Logs even when the URL contains `view=conversations`, and
the page MUST NOT mount the Conversations view or issue conversation list/detail
API requests. Navigation, filtering, and conversation detail behavior for
principals with `conversations:read` MUST remain unchanged.

#### Scenario: Guest selector hides Conversations

- **GIVEN** the dashboard principal has role `guest`
- **WHEN** the Logs page renders
- **THEN** it shows Request Logs and does not expose Conversations

#### Scenario: Guest conversation deep link falls back safely

- **GIVEN** the dashboard principal has role `guest`
- **AND** the URL contains `view=conversations`
- **WHEN** the Logs page renders
- **THEN** the effective view is Request Logs
- **AND** the Conversations view is not mounted
- **AND** no `/api/conversations` request is issued

#### Scenario: Conversation access fails closed during auth hydration

- **GIVEN** auth initialization is incomplete
- **AND** the URL contains `view=conversations`
- **WHEN** the Logs page renders before the session resolves
- **THEN** Request Logs is shown and the Conversations view is not mounted
- **AND** no conversation request is enabled
- **AND** the URL retains `view=conversations`
- **WHEN** the session resolves to a guest principal
- **THEN** the conversation surface remains closed and the URL is normalized to
  Request Logs

#### Scenario: Admin retains Conversations navigation

- **GIVEN** the dashboard principal has role `admin`
- **WHEN** the Logs page renders
- **THEN** the view toggle exposes both Request Logs and Conversations

### Requirement: Dashboard routes are code-split

Each dashboard route's page component MUST load lazily so the entry chunk excludes the code of pages the operator has not visited; the built entry chunk MUST NOT statically import or modulepreload page chunks.

#### Scenario: Entry chunk excludes unvisited pages

- **WHEN** the dashboard entry page loads
- **THEN** only the visited route's page chunk is fetched
- **AND** the built entry chunk neither statically imports nor modulepreloads the other pages' chunks

### Requirement: Dashboard assets are fully self-hosted

The dashboard MUST NOT load fonts or other render-blocking resources from external origins; all font assets ship with the build and declare `font-display: swap`.

#### Scenario: No external origins in the built shell

- **WHEN** the dashboard shell is built
- **THEN** `index.html` and the emitted assets reference no external font or stylesheet origins

#### Scenario: First paint proceeds without network egress

- **GIVEN** a deployment without outbound internet access
- **WHEN** an operator loads the dashboard
- **THEN** first paint is not blocked on any external request and monospace text renders via the bundled font or the system fallback

### Requirement: Dashboard supports Korean runtime locale

The dashboard SHALL support Korean (`ko`) as a runtime locale in addition to
English (`en`) and Simplified Chinese (`zh-CN`). Korean language detection SHALL
select `ko` for browser language tags whose base language is `ko`, and the
language switcher SHALL let users choose Korean without reloading the page.

#### Scenario: First visit with a Korean browser

- **WHEN** a user opens the dashboard for the first time with `navigator.language = "ko-KR"` and no persisted preference
- **THEN** the dashboard renders the translated in-scope surface in Korean
- **AND** `localStorage` contains `codex-lb-language=ko`
- **AND** `document.documentElement.lang` is set to `ko`

#### Scenario: User toggles Korean

- **WHEN** the user activates the language switcher and selects Korean
- **THEN** the dashboard re-renders translated strings in Korean without a full page reload
- **AND** the selected language persists across reloads

### Requirement: Dashboard feature surfaces render in the active locale

Dashboard feature surfaces SHALL render user-visible copy through the active
i18n locale, including page headings, section headings, empty states, table
headings, filter labels, button labels, accessible labels, dialog titles,
dialog descriptions, validation messages, and client-side toast fallback copy.
This requirement applies to Accounts, Dashboard, API Keys, APIs, Reports,
Automations, Firewall, Model Sources, Quota Planner, Sticky Sessions, Settings
subsections, and shared dashboard components.

The dashboard MAY keep protocol names, product names, model/API terminology,
quota window abbreviations, and compact operational abbreviations in English
when the English form is the clearest operator-facing label.

#### Scenario: Korean feature page rendering

- **WHEN** a user selects `ko`
- **AND** opens Accounts, Dashboard, API Keys, APIs, Reports, Automations, Firewall, Model Sources, Quota Planner, Sticky Sessions, or Settings subsections
- **THEN** user-visible labels, headings, empty states, dialog copy, accessible labels, and client-side toast fallback copy render in Korean
- **AND** technical terms such as `API Key`, `Model`, `TOTP`, `OAuth`, `TTFT`, `TPS`, and `Fast Mode` MAY remain English where appropriate

#### Scenario: Simplified Chinese feature page rendering

- **WHEN** a user selects `zh-CN`
- **AND** opens a dashboard feature page beyond the original auth/header/settings coverage
- **THEN** newly migrated user-visible strings render in Simplified Chinese
- **AND** the page does not fall back to English because a locale key is missing

#### Scenario: Locale bundles stay in sync

- **WHEN** the frontend locale bundles are compared
- **THEN** `en`, `zh-CN`, and `ko` expose the same translation keys

### Requirement: Reports endpoint rejects inverted date ranges before repository work

After applying defaults for any omitted date bound, the Reports service MUST reject a `start_date` later than `end_date` before converting report boundaries or awaiting any repository operation. `GET /api/reports` MUST map that domain failure to HTTP 400 with the exact dashboard envelope `{"error":{"code":"invalid_report_date_range","message":"start_date must be on or before end_date"}}`. Valid one-day ranges and valid inclusive ranges of 730 calendar days MUST remain accepted.

#### Scenario: Explicit inverted Reports range is rejected

- **WHEN** an authenticated operator requests `GET /api/reports` with `start_date` later than `end_date`
- **THEN** the endpoint returns HTTP 400
- **AND** the response body is exactly `{"error":{"code":"invalid_report_date_range","message":"start_date must be on or before end_date"}}`
- **AND** the Reports repository receives no call

#### Scenario: Defaulted end date makes the range inverted

- **WHEN** an authenticated operator requests `GET /api/reports` with an explicit `start_date` later than the defaulted current `end_date`
- **THEN** the endpoint returns the same `invalid_report_date_range` HTTP 400 before repository work

#### Scenario: Boundary-valid Reports ranges remain accepted

- **WHEN** an authenticated operator requests a one-day range whose `start_date` equals `end_date`
- **THEN** the endpoint accepts the request and reports data for that day
- **WHEN** an authenticated operator requests an inclusive range of exactly 730 calendar days
- **THEN** the endpoint accepts the request under the existing range limit

### Requirement: Dashboard overview and request-log listing fail independently

The Dashboard SHALL gate overview-backed statistics, quota, projections, and account controls only on dashboard overview availability. The Request Logs section SHALL own the initial loading, terminal error, and ready states of its listing query without hiding healthy overview-backed content.

When the initial request-log listing reaches a terminal error, the Request Logs section MUST remain visible, MUST render the listing error inside that section, MUST announce that error through an alert semantic local to the section, and MUST expose a keyboard-operable, accessibly named Retry action. Activating Retry MUST refetch only the request-log listing query and MUST NOT refetch or hide healthy overview-backed content.

While the initial overview request is pending with no data, the Dashboard SHALL
render the existing page-wide skeleton. When that request reaches a terminal
error with no data, it MUST NOT render the skeleton; it MUST preserve the shell,
MUST announce the error, and MUST expose a keyboard-operable Retry.

Retry SHALL refetch only the overview query. The terminal error SHALL remain
rendered and Retry SHALL remain disabled with a busy state while that no-data
refetch is in flight. Successful refetch SHALL replace the error with overview
content. Cached overview data SHALL remain visible on later refetch errors.

#### Scenario: Initial request-log failure preserves healthy overview

- **GIVEN** dashboard overview, projections, and request-log filter options load successfully
- **WHEN** the initial request-log listing reaches a terminal error
- **THEN** overview statistics, quota, and account content remain rendered
- **AND** the page-wide Dashboard loading skeleton is not rendered
- **AND** the Request Logs section contains and announces the listing error and exposes a Retry action

#### Scenario: Request-log retry recovers independently

- **GIVEN** healthy overview-backed content is rendered and the initial request-log listing has failed
- **WHEN** the listing endpoint recovers and the operator activates Retry
- **THEN** only the request-log listing query is refetched
- **AND** healthy overview-backed content remains visible throughout recovery
- **AND** the recovered request-log rows render in the Request Logs section

#### Scenario: Request logs load inside their section

- **GIVEN** dashboard overview data is available
- **WHEN** the initial request-log listing is still pending
- **THEN** overview-backed content is rendered
- **AND** the Request Logs section renders its own loading state
- **AND** the page-wide Dashboard loading skeleton is not rendered

#### Scenario: Initial overview loading keeps the existing page skeleton

- **WHEN** the dashboard overview is not yet available
- **THEN** the Dashboard renders its existing page-wide loading skeleton
- **AND** it does not render overview-backed content prematurely

#### Scenario: Terminal overview failure replaces the skeleton

- **GIVEN** no overview data is available
- **WHEN** the overview query reaches terminal error
- **THEN** shell landmarks remain mounted
- **AND** the loading skeleton is removed
- **AND** an alert and keyboard-operable Retry are rendered

#### Scenario: Retry remains visible while fetching

- **GIVEN** the terminal no-data error is rendered
- **WHEN** the operator activates Retry
- **THEN** only the overview query refetches
- **AND** the error remains visible
- **AND** Retry is disabled and exposes a busy state

#### Scenario: Retry recovers in place

- **WHEN** the endpoint succeeds after Retry
- **THEN** overview content replaces the error without a full page reload

#### Scenario: Cached overview survives later failure

- **GIVEN** overview content already exists
- **WHEN** a later refetch fails
- **THEN** the content remains visible without a page-wide skeleton

### Requirement: App header brand links to dashboard

The app header brand area SHALL render a `<Link to="/dashboard">` wrapping the
logo and "Codex LB" text so that clicking the brand navigates back to the
dashboard home page. The link SHALL preserve the existing visual layout (logo
size, gradient background, text styling) and SHALL include keyboard
focus-visible ring styling matching the project's existing interactive-element
conventions.

#### Scenario: Brand click navigates to dashboard

- **WHEN** an operator clicks the header brand area (logo or "Codex LB" text)
- **THEN** the SPA navigates to `/dashboard`

#### Scenario: Brand link is keyboard-accessible

- **WHEN** an operator tabs to the header brand
- **THEN** the brand area receives a visible focus ring
- **AND** pressing Enter navigates to `/dashboard`

#### Scenario: Brand link preserves visual appearance

- **WHEN** the header renders
- **THEN** the logo and "Codex LB" text appear visually identical to the prior
  non-interactive `<div>` layout

### Requirement: Dashboard metrics expose conversation-bearing requests

The dashboard overview response MUST expose
`summary.metrics.conversationRequests` as the count of non-warmup request-log
rows in the selected timeframe whose trimmed `conversation_id` is nonblank.
The existing `requests` field MUST continue counting all non-warmup rows, and
the existing `conversations` field MUST continue counting distinct nonblank
conversation IDs in that timeframe.

#### Scenario: Requests without conversation IDs are excluded from the new count

- **GIVEN** a timeframe contains four requests with nonblank conversation IDs
  and two requests with null or whitespace-only IDs
- **WHEN** the dashboard overview is requested
- **THEN** `conversationRequests` is `4`
- **AND** `requests` includes all six non-warmup requests

### Requirement: Dashboard conversation card shows the filtered average

The dashboard conversation card MUST be labeled `Active Conversations` with
the selected timeframe, and its secondary metadata MUST show `Avg req/conv`
followed by `conversationRequests / conversations`, formatted to one decimal
place. When `conversations` is zero, the metadata MUST show an em dash instead
of dividing by zero.

#### Scenario: Average uses only conversation-bearing requests

- **GIVEN** `conversationRequests` is `5` and `conversations` is `2`
- **WHEN** the dashboard card is rendered
- **THEN** its metadata shows `Avg req/conv 2.5`

#### Scenario: Average is safe when no conversations exist

- **GIVEN** `conversationRequests` is `4` and `conversations` is `0`
- **WHEN** the dashboard card is rendered
- **THEN** its metadata shows `Avg req/conv —`

### Requirement: Dashboard and report labels identify active conversations

The dashboard and report conversation summary cards MUST use the localized
equivalent of `Active Conversations`; their numeric values and ordering MUST
remain unchanged. The report card MUST NOT gain the dashboard average.

#### Scenario: Report uses the active-conversation label

- **WHEN** the report summary cards render
- **THEN** the conversation card label is `Active Conversations` in English
- **AND** its numeric value remains the existing distinct conversation total
- **AND** no `Avg req/conv` metadata is rendered on the report card

### Requirement: Simplified Chinese locale bundle covers all dashboard keys

The `zh-CN` locale bundle SHALL provide an entry for every user-visible i18n
key present in the `en` bundle, so no dashboard surface falls back to English
because of a missing key. Values MAY keep protocol names, product names,
model/API terminology, and compact operational abbreviations in English when
the English form is the clearest operator-facing label.

#### Scenario: zh-CN rendering without English fallback

- **WHEN** a user selects `zh-CN`
- **AND** opens Accounts, Dashboard, API Keys, APIs, Reports, Automations, Firewall, Model Sources, Quota Planner, Sticky Sessions, Upstream Proxy, or Settings subsections
- **THEN** user-visible labels, headings, empty states, dialog copy, accessible labels, and client-side toast fallback copy render through the `zh-CN` bundle
- **AND** no string falls back to English because of a missing locale key
- **AND** technical terms such as `API Key`, `Model`, `OAuth`, `TOTP`, `Credits`, and `Quota` MAY remain English where appropriate

### Requirement: zh-CN terminology stays consistent across feature surfaces

Translated `zh-CN` strings SHALL reuse established dashboard terminology for
repeated concepts, and labels that sit inside a label group whose siblings are
already translated SHALL render in Simplified Chinese as well.

#### Scenario: Consistent wording for repeated concepts

- **WHEN** a concept already has an established `zh-CN` translation on one surface (e.g. 账户消耗预测 in the settings appearance section)
- **THEN** other surfaces referencing the same concept reuse that wording instead of introducing a synonym

#### Scenario: Mixed-label groups render fully in Chinese

- **WHEN** a filter group or table header contains several labels and some already render in Simplified Chinese (e.g. 状态, 类型)
- **THEN** the remaining labels in that group render in Simplified Chinese (e.g. 触发方式) instead of falling back to English

### Requirement: Dashboard numeric units stay locale-independent

Dashboard quantities that use compact formatting SHALL use `K`, `M`, and `B`
suffixes regardless of the selected interface locale so requests, tokens,
balances, pool totals, projections, and configured thresholds remain directly
comparable. Dashboard USD values SHALL use the `$` prefix across locales.

#### Scenario: Simplified Chinese compact quantity display

- **WHEN** a user selects `zh-CN`
- **AND** views compact request, token, or credit quantities
- **THEN** 10,200 renders as `10.2K`
- **AND** 1,500,000 renders as `1.5M`
- **AND** 1,500,000,000 renders as `1.5B`
- **AND** 12 USD renders as `$12.00`

### Requirement: Reports per-day averages use the inclusive local calendar window

`GET /api/reports` MUST calculate `summary.avgCostPerDay` and
`summary.avgRequestsPerDay` by dividing the current report totals by exactly
`(end_date - start_date).days + 1`. The divisor MUST represent the selected
inclusive local calendar-date window and MUST NOT be derived from the
UTC-converted filter boundaries.

#### Scenario: Offset-to-zero transition keeps a two-day divisor

- **WHEN** an operator requests `2026-02-15` through `2026-02-16` in
  `Africa/Casablanca` and the report totals are 60 cost units and 30 requests
- **THEN** `avgCostPerDay` is `30`
- **AND** `avgRequestsPerDay` is `15`

#### Scenario: Offset-from-zero transition keeps a two-day divisor

- **WHEN** an operator requests `2026-03-22` through `2026-03-23` in
  `Africa/Casablanca` and the report totals are 60 cost units and 30 requests
- **THEN** `avgCostPerDay` is `30`
- **AND** `avgRequestsPerDay` is `15`

### Requirement: Dashboard status separates service readiness from usage synchronization

The fixed dashboard status bar MUST render independent `Service ready` and
`Usage synced` signals. `Service ready` MUST use the existing `/health/ready`
response and MUST treat a failed request or a non-`ok` status as not ready.
`Usage synced` MUST remain derived only from the dashboard overview
`lastSyncAt` value and MUST be fresh only while that timestamp is less than 60
seconds old. The service-readiness signal MUST NOT use upstream account or
provider health. The dashboard layout MUST reserve at least the status bar's
rendered height so wrapped status rows do not cover page content.

#### Scenario: Ready service with stale usage

- **WHEN** `/health/ready` returns `status: "ok"`
- **AND** `lastSyncAt` is absent or at least 60 seconds old
- **THEN** the status bar shows the service as ready
- **AND** independently shows usage as stale

#### Scenario: Unready service with fresh usage

- **WHEN** `/health/ready` fails or returns a non-`ok` status
- **AND** `lastSyncAt` is less than 60 seconds old
- **THEN** the status bar shows the service as not ready
- **AND** independently shows usage as synced

#### Scenario: Readiness is still being checked

- **WHEN** the initial `/health/ready` request has not completed
- **THEN** the service-readiness signal shows a checking state
- **AND** the usage synchronization signal remains independently derived from
  `lastSyncAt`

#### Scenario: Status signals wrap onto additional rows

- **WHEN** the fixed status bar grows because its signals wrap
- **THEN** the dashboard updates its reserved bottom space to the rendered
  status-bar height
- **AND** the fixed status bar does not cover page content

### Requirement: Dashboard conversation listing

The authenticated dashboard MUST expose `GET /api/conversations`. The list
endpoint MUST accept `limit`, `offset`, `search`, `since`, and `timeframe` query
parameters. The server-authoritative `timeframe` parameter MUST accept `1d`,
`7d`, or `30d`; when it is supplied, the server MUST derive the activity window
from the shared dashboard timeframe configuration and the client MUST NOT
substitute a browser-clock-generated `since` value. `timeframe` and `since` MUST
not be supplied together. When `since` is omitted, the server MUST apply a
rolling 30-day lower bound;
explicitly older `since` values MUST be capped at that same bound, and incoming
timezone-aware datetimes MUST be normalized to naive UTC before querying. It
MUST aggregate eligible `request_logs` rows by the raw, non-empty
`conversation_id` column, excluding rows whose request kind is `warmup` or
`limit_warmup`, and rows with `deleted_at IS NOT NULL`. Production request-log
writes MUST normalize ASCII padding and blank conversation IDs before storage;
conversation list, facet, and detail queries MUST use raw-column
`conversation_id` predicates and grouping rather than function-wrapped
expressions.

Search MUST be case-insensitive and match the normalized conversation ID or any
eligible row's user-agent family. Search MUST select whole conversations first:
after a conversation matches, aggregation MUST include all eligible rows in that
conversation, including rows whose user-agent family or ID did not match the
search text. The endpoint MUST derive aggregates from `request_logs` only.

When `since` is provided, a conversation MUST be selected when at least one
eligible row has `requested_at >= since`. A conversation MAY have eligible rows
before `since` and MUST still be included when it has activity in the window.
The grouped summary MUST aggregate all eligible rows for every selected
conversation, so `firstRequest`, `lastRequest`, `requestCount`, token totals,
cached-token totals, and cost MUST NOT be clipped to the window. Membership MUST
be implemented as an in-window aggregate condition and MUST NOT use a global
pre-window ID set or a pre-window anti-join.

After page membership is selected, the account, API-key, and model facet
queries for the returned page MUST use the same full eligible-row scope as the
summary, restricted only by the selected page's raw `conversation_id` values.
The facet queries MUST NOT add a `requested_at >= since` restriction after
membership selection; facet representatives and remaining counts MUST include
eligible history before `since` and MUST remain consistent with the full-history
summary aggregates.

The response MUST contain `conversations`, `total`, and `hasMore` pagination
fields. Each row in `conversations` MUST contain exactly these fields and no
response summary object:

- `conversationId`: the normalized, non-empty conversation identity.
- `firstRequest`: the earliest `requested_at` among all eligible rows in the
  conversation.
- `lastRequest`: the latest `requested_at` among all eligible rows in the
  conversation.
- `requestCount`: the number of eligible rows in the conversation.
- `representativeAccount` and `remainingAccountCount`.
- `apiKeyId` and `apiKeyName`.
- `representativeModel` and `remainingModelCount`.
- `totalTokens`.
- `cachedInputTokens`.
- `totalCostUsd`.

The camelCase names above are the external Dashboard API JSON contract. Python
schema, service, and repository identifiers MAY remain snake_case internally;
internal names MUST NOT be emitted as alternate response fields.

`totalTokens` MUST equal total input tokens plus total output tokens, with
`reasoning_tokens` used for a row when `output_tokens` is null.
`cachedInputTokens` MUST use the existing per-row clamp: null remains null;
otherwise the cached value is clamped to `[0, input_tokens]` when input tokens
are present. At aggregate level, null per-row values MUST NOT be converted to
zero; when every eligible row has a null cached value, `cachedInputTokens` MUST
be null, and otherwise it MUST equal the sum of the known clamped values.

Representative account values MUST use `request_count DESC,
latest_requested_at DESC, lexical account ASC`. List model values MUST be
grouped by distinct model, combining all reasoning efforts for that model, and
the representative model MUST use `request_count DESC, latest_requested_at DESC,
model lexical ASC`. Null account values MUST be excluded from account
candidates; if no non-null account exists, `representativeAccount` MUST be null
and `remainingAccountCount` MUST be 0. The list MUST NOT split model values by
`reasoning_effort`; `(model, reasoning_effort)` grouping MUST be used only for
conversation details.

Nullable and multiple-key conversations MUST be handled deterministically. Null
API-key values MUST not be candidates; if no non-null key exists, both API-key
fields MUST be null. When multiple distinct non-null keys exist, `apiKeyId` MUST be selected by
`request_count DESC, latest_requested_at DESC, lexical API-key ID ASC`, and
`apiKeyName` MUST be the corresponding existing dashboard-safe display name.
`apiKeyName` MUST never expose a secret, hash, or plaintext key material.

The list order MUST be stable: `lastRequest DESC`, then normalized
`conversationId ASC`. Pagination MUST be applied after this ordering.

#### Scenario: Pagination uses the stable list order

- **GIVEN** matching conversations have different latest request times and a
  tie exists on `lastRequest`
- **WHEN** the client calls `GET /api/conversations?limit=10&offset=20`
- **THEN** rows are ordered by `lastRequest DESC` and ties by normalized
  `conversationId ASC`
- **AND** the response starts at the 21st row in that order and reports the
  matching total and whether another page exists

#### Scenario: Blank IDs, warmups, and soft-deleted rows are excluded

- **GIVEN** request logs include null IDs, whitespace-only IDs, `warmup` rows,
  `limit_warmup` rows, soft-deleted rows, and eligible rows with non-empty IDs
- **WHEN** the client calls `GET /api/conversations`
- **THEN** only rows whose request kind is neither `warmup` nor `limit_warmup`,
  which are non-soft-deleted and have non-empty normalized IDs, contribute to
  returned conversations

#### Scenario: Search selects whole conversations

- **GIVEN** one eligible conversation contains a matching user-agent family on
  one row and non-matching user-agent/ID values on other rows
- **WHEN** the client calls `GET /api/conversations?search=opencode`
- **THEN** that conversation is selected
- **AND** all eligible rows in that conversation contribute to its counts,
  tokens, cached tokens, and cost
- **AND** rows from conversations with no matching ID or user-agent family are
  not returned

#### Scenario: List search is case-insensitive over normalized IDs and user-agent families

- **GIVEN** an eligible conversation has a normalized ID and user-agent family
  whose letters differ in case from the search text
- **WHEN** the client calls `GET /api/conversations?search=OPENCODE`
- **THEN** the conversation is selected when either the normalized ID or any
  eligible row's user-agent family matches case-insensitively

#### Scenario: Since filter selects conversations active in the window

- **GIVEN** conversation `conv-old` has its earliest eligible row at `t-10d`
  and a later row at `t-1d`, and conversation `conv-new` has its earliest
  eligible row at `t-1d`
- **WHEN** the client calls `GET /api/conversations?since=<t-7d ISO>`
- **THEN** both `conv-new` and `conv-old` are returned
- **AND** `conv-old` is included because it has a row inside the window even
  though its first message predates the window
- **AND** both conversations' summaries aggregate every eligible row, not only
  rows at or after `since`

#### Scenario: Since membership and facets share the full conversation scope

- **GIVEN** a selected conversation has eligible account, API-key, and model
  values both before and after the `since` boundary
- **WHEN** the client calls `GET /api/conversations?since=<ISO>`
- **THEN** `firstRequest`, `lastRequest`, `requestCount`, and summary totals
  include all eligible rows for the conversation
- **AND** account, API-key, and model facet counts and representatives include
  all eligible rows in the selected conversation, including rows before `since`

#### Scenario: Since filter composes with search and pagination

- **GIVEN** two conversations have activity inside the `since` window and only
  one matches the search text
- **WHEN** the client calls `GET /api/conversations?since=<ISO>&search=opencode`
- **THEN** only the matching conversation is returned
- **AND** the response total and hasMore reflect the since-and-search filtered
  set

#### Scenario: List model representatives ignore reasoning effort

- **GIVEN** a conversation has requests for the same model with multiple
  reasoning-effort values and requests for another model
- **WHEN** the client calls `GET /api/conversations`
- **THEN** the list groups the same model's requests into one model value
- **AND** the representative model is ordered by request count descending,
  latest request descending, and model lexical ascending
- **AND** the remaining model count counts distinct models, not model/effort
  combinations

#### Scenario: API-key representation is safe and deterministic

- **GIVEN** a conversation has null API-key rows and multiple non-null API-key
  values with tied counts
- **WHEN** the client calls `GET /api/conversations`
- **THEN** null values do not become the representative
- **AND** the non-null representative is selected by count, latest request, and
  lexical API-key ID
- **AND** the response contains only the corresponding dashboard-safe name and
  never secret, hash, or plaintext key material

### Requirement: Dashboard conversation activity uses the list eligibility scope

The dashboard overview conversation metrics and per-bucket conversation trend
MUST use the same eligible `request_logs` row scope as the conversation list:
non-empty conversation IDs, request kinds other than `warmup` and
`limit_warmup`, and `deleted_at IS NULL`. This scope MUST apply to both the
distinct conversation count and conversation request count in the overview
summary and to each conversation trend bucket.

#### Scenario: Soft-deleted-only conversations are absent from dashboard activity

- **GIVEN** the selected timeframe contains an eligible conversation and a
  second conversation whose only rows are soft-deleted
- **WHEN** the client requests the conversation list and dashboard overview for
  that timeframe
- **THEN** the list total and summary conversation count include only the
  eligible conversation
- **AND** the summary conversation request count and conversation trend contain
  no contribution from the soft-deleted-only conversation

### Requirement: Conversation listing total is served from a short-TTL cache

The grouped `total` returned by `GET /api/conversations` is display-only
pagination metadata that tolerates short staleness, and the dashboard polls the
endpoint every 30 seconds. Recomputing the grouped count over the full eligible
`request_logs` history on every poll risks the same dashboard-induced
database contention this repository has previously optimized away.

The conversation listing total MUST be served from the same short-TTL
per-filter-signature cache as the request-log listing total (fixed 30 s TTL
application constant; bounded LRU-ish eviction; per-instance). The cache
signature MUST include every dimension that changes the grouped count: `search`
and the semantic window identity MUST be included, using
`("timeframe", timeframe)` for server-authoritative timeframe requests and
`("since", effective_since)` for legacy `since` requests. `limit` and `offset`
MUST be excluded from the signature because the total is page-independent. Two
requests with different search text or window identities MUST NOT reuse one
another's cached total.

#### Scenario: Repeated polls reuse the cached conversation total

- **GIVEN** the conversation listing has computed a total for a given
  `search` and semantic window signature
- **WHEN** the dashboard polls the same endpoint within the TTL with the same
  signature
- **THEN** the grouped count MUST NOT be recomputed
- **AND** the response total MUST equal the previously computed value

#### Scenario: Different window signatures isolate cached conversation totals

- **GIVEN** two listing requests differ only by their timeframe or legacy
  `since` window
- **WHEN** their totals are served through the cache
- **THEN** each request MUST use its own cache entry and grouped total

#### Scenario: Search participates in the conversation total cache signature

- **GIVEN** two listing requests differ only by the `search` text
- **WHEN** their totals are served through the cache
- **THEN** each request MUST use its own cache entry and grouped total

### Requirement: Conversation details

The authenticated dashboard MUST expose
`GET /api/conversations/{conversation_id}`. Detail aggregation MUST use the same
eligible-row scope as listing: normalized non-empty IDs, rows whose request kind
is neither `warmup` nor `limit_warmup`, and `deleted_at IS NULL`.

For a matching conversation, the detail response MUST expose the conversation ID,
`start` (earliest `requested_at`), `latest` (latest `requested_at`),
`accountCount` (distinct non-null accounts), `totalElapsedTime`, and
`dominantUseragentGroup`. `totalElapsedTime` MUST be
`SUM(COALESCE(latency_ms, 0))` over all eligible rows, never the wall-clock span.
`dominantUseragentGroup` MUST use
`request_count DESC, latest_requested_at DESC, lexical ASC`.

The response MUST include one model/effort row per distinct
`(model, reasoning_effort)` combination. Each row MUST contain exactly:
`modelEffort`, `reqs`, `totalElapsedTime`, `totalInputTokens`,
`cachedInputTokens`, `totalOutputTokens`, and `totalCostUsd`. The row
elapsed time MUST use `SUM(COALESCE(latency_ms, 0))` for that combination;
output tokens MUST use the reasoning-token fallback; cached input MUST use the
existing per-row clamp. No error-count or other column may be returned.

The API MUST order model/effort rows by `reqs DESC`, latest request DESC, and
lexical key ASC. It MUST NOT accept a sort query parameter. Client-side sorting
MUST operate only on returned rows.

An encoded blank path such as `GET /api/conversations/%20` MUST return the
project-standard 404 response. An unknown non-empty conversation ID MUST also
return the project-standard 404 response. The detail route MUST accept any
normalized non-empty stored conversation ID, including IDs containing `/`, when
the client percent-encodes the opaque ID as one path value.

#### Scenario: Details preserve cumulative elapsed time

- **GIVEN** a conversation has known latencies across multiple accounts and
  model/effort combinations
- **WHEN** the client calls `GET /api/conversations/conv-a`
- **THEN** conversation `totalElapsedTime` is the sum of
  `COALESCE(latency_ms, 0)` across eligible rows
- **AND** each model/effort row uses the same cumulative sum over its matching
  rows rather than the start/latest wall-clock span

#### Scenario: Details exclude warmups and soft-deleted rows

- **GIVEN** a conversation contains normal, `warmup`, `limit_warmup`, and
  soft-deleted request logs
- **WHEN** the client calls `GET /api/conversations/conv-a`
- **THEN** the summary and every model/effort row include only rows whose request
  kind is neither `warmup` nor `limit_warmup` and which are non-soft-deleted

#### Scenario: Blank and unknown detail IDs use standard not-found behavior

- **WHEN** the client calls `GET /api/conversations/%20` or requests an unknown
  non-empty ID
- **THEN** the API returns the standard 404 error envelope

#### Scenario: Slash-containing detail IDs remain addressable

- **GIVEN** an eligible conversation has the normalized ID `workspace/thread-1`
- **WHEN** the client calls `GET /api/conversations/workspace%2Fthread-1`
- **THEN** the API returns that conversation's details with
  `conversationId` equal to `workspace/thread-1`

### Requirement: Dashboard conversation view

The dashboard MUST render Request Logs by default. The original uppercase
section-title typography MUST be retained, and the title itself MUST be the
single accessible Radix-style selector trigger with `ChevronDown` for Request
Logs and Conversations. A separate selector MUST NOT render to the title's
right. Selecting Conversations MUST persist `view=conversations` in the URL;
selecting Request Logs MUST return to the existing request-log view.

The dashboard MUST retain separate URL-backed query state for Request Logs and
Conversations, including each view's applicable filters and pagination.
Switching views MUST NOT reinterpret, overwrite, or clear the inactive view's
query state, and returning to a view MUST restore its retained state.

The Conversations view MUST NOT render a free-text filter input above the list.
The view MUST render a day-range selector with exactly three options — `1d`,
`7d`, and `30d` — placed at the top-right of the dashboard page alongside the
refresh action and shown only while the Conversations view is active. The
selector MUST default to `7d`. The selected value MUST be persisted in the URL
as `conversationTimeframe`, MUST drive the list endpoint's `timeframe` query
parameter using the same symbolic key (the server derives the effective window),
and MUST NOT generate a browser-clock-derived `since` parameter. It MUST reset
pagination to offset 0 on change. The selector's values and default
MUST mirror the dashboard overview timeframe selector, with no unbounded
"all" option. The view MUST use the list endpoint's
established loading, error, empty, and pagination behavior.
While Conversations is active, the dashboard overview query that supplies the
statistics cards MUST use the active `conversationTimeframe`, including on the
initial render when that value is restored from the URL. The independently
retained `overviewTimeframe` MUST continue to drive the overview query when
Request Logs is active.

The conversation list MUST render exactly these columns in order: Last request,
Conversation, Accounts, API key, Models, Tokens, Cost, and Details. Last request
MUST use the request-log Time column's two-line time/date presentation. Accounts
MUST resolve the representative account ID through the dashboard account
summaries and display `displayName`, then email, then the ID as a final fallback.
Accounts and models MUST render remaining values as a smaller muted `+ N more`
secondary line. Tokens MUST show total tokens with cached input tokens on a
subordinate line.
When dashboard privacy blur is enabled, an account label resolved from an email
fallback MUST render with the established `privacy-blur` class; display-name
and account-ID fallback labels MUST remain unblurred.
The API-key column MUST use `apiKeyName` only. Details MUST use the existing
Details button treatment.

The details dialog MUST render row one as conversation ID, start, and latest;
row two as account count, total elapsed time, and dominant user-agent family;
and a model/effort table with exactly these displayed columns, in order: Model
(effort), Reqs, Total elapsed, Total input (with total cache as a
subordinate/parenthetical value), Total output, and Total cost. Total cache MUST
not be a separate displayed column. The table MUST default to Reqs descending
and MUST support client-side sorting for every displayed column without adding a
sort query parameter.
The displayed conversation ID MUST NOT provide a copy action.

The detail dialog MUST use the established dashboard loading state while the
detail API is pending. Unknown or malformed conversation IDs, including a
standard detail API 404, MUST use the standard dashboard error display and retry
behavior. Nullable optional aggregate values MUST render the established
em-dash or other dashboard fallback value without breaking the row or dialog.
An empty conversation list MUST render the established dashboard empty state.
When an empty conversation list is returned for a nonzero pagination offset, the
Conversations view MUST retain its pagination controls so the operator can
navigate back to the first or previous page. The initial empty state at offset
zero MUST NOT render pagination controls.

#### Scenario: Request Logs is the default and selector switches views

- **WHEN** an operator opens the dashboard
- **THEN** Request Logs is visible and active by default
- **WHEN** the operator selects Conversations
- **THEN** the Conversations list renders and the URL contains
  `view=conversations`

#### Scenario: Request Logs and Conversations retain independent URL query state

- **GIVEN** Request Logs has active filters and pagination and Conversations has
  different active filters and pagination retained in the URL
- **WHEN** the operator switches between the two views
- **THEN** each view restores its own filters and pagination
- **AND** switching views does not reinterpret, overwrite, or clear the other
  view's query state

#### Scenario: Conversations has no free-text filter and renders the day selector

- **WHEN** the operator opens the Conversations view
- **THEN** no free-text filter input is rendered above the list
- **AND** a day-range selector with exactly `1d`, `7d`, and `30d` options is
  rendered at the top-right of the dashboard page alongside the refresh action
- **AND** the selector defaults to `7d` and no unbounded "all" option is offered
- **AND** the list renders the specified reordered columns and two-line request
  time presentation
- **AND** representative account IDs resolve to display name, then email, then ID
- **AND** smaller muted `+ N more` account/model secondary lines and cached
  tokens as a subordinate line are rendered

#### Scenario: Conversation day selector persists in the URL and drives timeframe

- **WHEN** the operator changes the Conversations day selector from `7d` to `30d`
- **THEN** the URL gains `conversationTimeframe=30d` (or drops the param when the
  default `7d` is selected)
- **AND** the list endpoint is called with `timeframe=30d`
- **AND** the list endpoint does not receive a browser-clock-derived `since`
- **AND** pagination resets to offset 0

#### Scenario: Conversation timeframe drives active dashboard statistics

- **GIVEN** the URL restores `conversationTimeframe=30d` while
  `overviewTimeframe` is absent or has a different value
- **WHEN** the operator opens the Conversations view
- **THEN** the statistics-card overview query uses the `30d` timeframe
- **AND** the conversation list uses `timeframe=30d`
- **AND** the independently retained overview timeframe remains unchanged
  for the Request Logs view

#### Scenario: Conversation day selector state is independent per view

- **GIVEN** the Conversations day selector is set to `30d`
- **WHEN** the operator switches to Request Logs and back to Conversations
- **THEN** the Conversations view restores its retained `30d` selector state
- **AND** the Request Logs view state is unaffected

#### Scenario: Conversation account privacy blur applies only to email fallback

- **GIVEN** dashboard privacy blur is enabled and account labels resolve using
  display name, email fallback, and account-ID fallback values
- **WHEN** the Conversations list renders
- **THEN** only the email-fallback label has the established `privacy-blur` class
- **AND** the display-name and account-ID fallback labels remain unblurred

#### Scenario: The original-styled title is the only view selector

- **WHEN** the list section renders
- **THEN** its uppercase title typography is retained
- **AND** activating the title opens the Request Logs/Conversations selector
- **AND** no separate selector is rendered to the title's right

#### Scenario: Conversation details use established loading and retry states

- **WHEN** the detail API is loading for a selected conversation
- **THEN** the dialog uses the established dashboard loading state
- **WHEN** the detail API returns an unknown or malformed-ID error
- **THEN** the dialog uses the standard dashboard error display with retry

#### Scenario: Nullable detail aggregates use dashboard fallbacks

- **GIVEN** a successful detail response contains nullable optional aggregate
  values
- **WHEN** the operator opens the details dialog
- **THEN** each nullable value renders the established em-dash or dashboard
  fallback without breaking the row or dialog

#### Scenario: Empty conversation results use the existing empty state

- **GIVEN** the conversation list response contains no rows
- **WHEN** the operator opens the Conversations view
- **THEN** the existing dashboard empty state is rendered

#### Scenario: Empty later conversation pages retain pagination controls

- **GIVEN** the operator is on a nonzero Conversations page and the list
  response contains no rows
- **WHEN** the Conversations view renders the response
- **THEN** the existing dashboard empty state is rendered
- **AND** pagination controls remain visible
- **AND** the first-page and previous-page controls provide a path back to
  earlier results

#### Scenario: Details dialog has the approved layout and sorting

- **WHEN** the operator opens a conversation's Details dialog
- **THEN** row one contains conversation ID/start/latest
- **AND** conversation ID has no copy action
- **AND** row two contains account count/total elapsed/dominant user-agent
- **AND** the table displays exactly Model (effort), Reqs, Total elapsed, Total
  input (with total cache as a subordinate/parenthetical value), Total output,
  and Total cost
- **AND** the table initially sorts by Reqs descending
- **AND** activating any displayed table column header reorders only the returned
  rows client-side

### Requirement: Conversation list exposes grouped request metrics

`GET /api/conversations` SHALL include `requestCount` and `firstRequest` for
every conversation. `requestCount` SHALL count all eligible request-log rows
in that conversation, and `firstRequest` SHALL be the earliest eligible
`requested_at`. Existing `lastRequest` SHALL remain the latest eligible
`requested_at`.

#### Scenario: A conversation aggregates request metrics

- **GIVEN** one conversation has eligible requests at 10:00, 10:07, and
  12:15
- **WHEN** the conversation list is requested
- **THEN** its `requestCount` is `3`
- **AND** its `firstRequest` is the 10:00 timestamp
- **AND** its `lastRequest` is the 12:15 timestamp
- **AND** warmup, limit-warmup, deleted, blank-ID, and otherwise ineligible
  rows do not affect those values

### Requirement: Conversation list renders metrics and readable duration

The dashboard SHALL render columns in this order: Last request, Lasted,
Conversation, Accounts, API key, Models, Requests, Tokens, Cost, Details.
The Lasted value SHALL use `lastRequest - firstRequest`, displaying `0s` for
zero duration, seconds for durations under one minute, `xm ys` for durations
under one hour, `xh ym` for durations under one day, and `xd yh` for durations
of at least one day. The conversation-ID cell SHALL be top-aligned.

#### Scenario: Duration uses two units and preserves zero

- **WHEN** a row spans 2 hours and 15 minutes
- **THEN** Lasted displays `2h 15m`
- **WHEN** a row spans 2 days and 3 hours
- **THEN** Lasted displays `2d 3h`
- **WHEN** firstRequest equals lastRequest
- **THEN** Lasted displays `0s`

### Requirement: Fair-share congestion threshold is configurable from routing settings

The dashboard routing settings MUST expose the API-key fair-share congestion threshold as a numeric field adjacent to the per-account capacity limits, accepting integers from 0 to 100 where 0 disables the gate, with null-inherits-environment semantics matching the per-account capacity overrides. Values outside 0-100 MUST be rejected by both the client-side validation and the settings API. The field's label, description, and validation copy MUST be localized in the en, ko, and zh-CN locale bundles.

#### Scenario: Threshold round-trips through the settings API

- **GIVEN** an operator sets the threshold to 80 in routing settings
- **WHEN** the settings are saved and reloaded
- **THEN** the field shows 80 and the settings API reports 80 as the effective value

#### Scenario: Migrated null row inherits the environment default

- **GIVEN** a deployment whose dashboard settings row predates the field (a migrated NULL column)
- **AND** an environment-configured threshold
- **WHEN** the effective settings are read
- **THEN** the effective value inherits the environment setting

#### Scenario: Out-of-range values are rejected

- **GIVEN** an operator enters 101 or a negative number
- **WHEN** they attempt to save
- **THEN** the client blocks the save and the settings API rejects the value if submitted directly

#### Scenario: Copy is localized in all three locales

- **GIVEN** the dashboard language is set to en, ko, or zh-CN
- **WHEN** routing settings render
- **THEN** the threshold label and description display in the selected locale

### Requirement: Appearance settings include date format toggle

The Appearance settings section SHALL include a "Date format" toggle row with two options: "Default" and "ISO 8601". The toggle SHALL be placed between the Time format and Account rows settings. Selecting an option SHALL immediately apply the new format to applicable read-only date/time presentation text across the dashboard.

#### Scenario: Default date format is selected initially

- **WHEN** a user opens the Appearance settings section with no prior date format preference
- **THEN** the "Default" option SHALL be selected (aria-pressed true)
- **AND** applicable read-only date/time presentation text SHALL render using locale-dependent formatting

#### Scenario: Switching to ISO 8601

- **WHEN** the user clicks the "ISO 8601" option in the Date format row
- **THEN** the "ISO 8601" option SHALL be selected
- **AND** request log and conversation table cells SHALL display date on the top line in `YYYY-MM-DD` format and time on the bottom line in `HH:MM:SS` format
- **AND** the preference persists across page reloads

### Requirement: Accounts and API trend chart x-axis uses MM-DD format

The x-axis tick format of the Account Trend and API Trend charts SHALL be `MM-DD` (month and day extracted from the ISO timestamp data key), matching the reports chart convention. This format SHALL be locale-independent.

#### Scenario: Account trend chart x-axis ticks

- **WHEN** the Account Trend chart renders with timestamp data
- **THEN** the x-axis tick labels SHALL be in `MM-DD` format (e.g., `"08-09"`)

#### Scenario: API trend chart x-axis ticks

- **WHEN** the API Trend chart renders with timestamp data
- **THEN** the x-axis tick labels SHALL be in `MM-DD` format (e.g., `"08-09"`)

### Requirement: Dashboard refresh cadence is operator-selectable

The dashboard MUST let the operator select a 5, 15, 30, or 60 second refresh
cadence. The selection MUST persist locally, default to 15 seconds, and apply to
both overview and projection queries without enabling background-tab polling.
Failed refreshes MUST retain the last successful query data.

#### Scenario: Refresh cadence updates live dashboard queries

- **GIVEN** the operator selects a 5-second dashboard refresh cadence
- **WHEN** the dashboard overview and projection queries are active
- **THEN** both queries poll every 5 seconds
- **AND** the preference survives a page reload
- **AND** a failed poll does not clear the last successful data

### Requirement: First-run empty lists describe setup, not filter mismatch

Providers, API Keys, and dashboard request-log empty states SHALL distinguish a
first-run empty source list from a filtered-empty result. When the source
list has no items and no narrowing filter is applied, the empty copy SHALL
describe setup (no accounts yet, no API keys yet, no requests yet) and SHALL
NOT tell the operator to adjust filters. When the source list has items, or
request-log filters differ from their defaults, and the visible result is
empty, the empty copy SHALL describe a filter mismatch.

#### Scenario: Accounts first-run empty copy

- **GIVEN** the Providers page has no accounts
- **WHEN** the account list renders
- **THEN** the empty title describes that there are no accounts yet
- **AND** the empty description does not tell the operator to adjust filters

#### Scenario: Accounts filtered empty copy

- **GIVEN** the Providers page has at least one account
- **AND** the current search or status filter matches none of them
- **WHEN** the account list renders
- **THEN** the empty title describes that no accounts match
- **AND** the empty description tells the operator to adjust filters

#### Scenario: APIs first-run empty copy

- **GIVEN** the API Keys page has no API keys
- **WHEN** the API key table renders
- **THEN** the empty title describes that there are no API keys yet
- **AND** the empty description does not tell the operator to adjust filters

#### Scenario: API keys filtered empty copy

- **GIVEN** the API Keys page has at least one key
- **AND** the current search or filter matches none of them
- **WHEN** the API key table renders
- **THEN** the empty title describes that no API keys match

#### Scenario: Request logs first-run empty copy

- **GIVEN** the request-log listing has no rows
- **AND** request-log filters are at their defaults
- **WHEN** the recent-requests table renders
- **THEN** the empty title is `No requests yet`
- **AND** the empty description does not say that request logs match the current filters

#### Scenario: Request logs filtered empty copy

- **GIVEN** the request-log listing has no rows
- **AND** at least one request-log filter differs from its default
- **WHEN** the recent-requests table renders
- **THEN** the empty copy describes that no request logs match the current filters

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

### Requirement: Sticky-threads copy distinguishes soft routing from hard continuation affinity

The routing settings SHALL describe `Sticky threads` as a soft preference and
SHALL state that disabling it does not disable hard Codex continuation
affinity for requests that carry continuation state.

#### Scenario: Sticky threads help copy

- **WHEN** the routing settings section renders
- **THEN** the sticky-threads description identifies the toggle as a soft preference
- **AND** an adjacent note states that hard Codex continuation affinity is not disabled by the toggle

### Requirement: Sticky thresholds are presented in percent used with a remaining equivalent

The sticky reallocation threshold controls SHALL name the quota window they
apply to, SHALL state that the value is percent used, and SHALL show the
quota-arithmetic remaining percent for a valid threshold value, qualified so
it is not presented as the exact account-page remaining figure (routing adds
temporary in-flight pressure on top of reported usage).

#### Scenario: Threshold unit hint

- **GIVEN** the sticky secondary threshold input holds the valid value `70`
- **WHEN** the routing settings section renders
- **THEN** a hint shows `70% used` alongside `30% remaining` in quota terms
- **AND** the quota-window explainer states that in-flight work counts as temporary extra usage

#### Scenario: Quota window explainer

- **WHEN** the routing settings section renders
- **THEN** an explainer identifies primary quota as the 5-hour window and secondary quota as the longer weekly window (monthly on plans without a weekly window)
- **AND** it states that account pages show percent remaining while the thresholds are percent used

### Requirement: Prefer-earlier-reset and limit warm-up copy describe actual behavior

The routing settings SHALL describe `Prefer earlier reset` as preferring
otherwise-eligible accounts whose selected quota window resets sooner. The
limit warm-up feature SHALL be labeled "Window warm-up" throughout the dashboard,
and its description SHALL state that it starts opted-in accounts' usage windows
early so they reset sooner, and that its requests are real and consume a small
amount of quota. Internal API, database and request-log identifiers keep the
`limit_warmup` name.

#### Scenario: Prefer earlier reset help copy

- **WHEN** the routing settings section renders
- **THEN** the prefer-earlier-reset description says selection prefers accounts whose selected quota window resets sooner
- **AND** it names the strategies the preference applies to (capacity weighted, usage weighted, and fill first)

#### Scenario: Limit warm-up help copy

- **WHEN** the routing settings section renders
- **THEN** the feature is labeled "Window warm-up"
- **AND** its description says it starts opted-in accounts' usage windows early so they reset sooner
- **AND** it states that the requests are real and consume a small amount of quota

### Requirement: Active status is presented as displayed status, not per-request eligibility

The accounts list SHALL present a visible note that displayed status does not
guarantee per-request eligibility, and SHALL annotate active rows and their
status badges with the same hint for pointer and assistive-technology users.

#### Scenario: Accounts list eligibility note

- **GIVEN** the accounts list contains at least one account
- **WHEN** the list renders
- **THEN** a visible note states that individual requests can still skip an `Active` account

#### Scenario: Active badge eligibility hint

- **GIVEN** an account whose status is `active`
- **WHEN** its accounts-list entry renders
- **THEN** the focusable account row and the status badge carry the hint as a native tooltip and accessible description
- **AND** non-active statuses do not carry that hint

### Requirement: Configurable dashboard request-log columns

The dashboard SHALL let operators show or hide request-log columns and MUST
preserve at least one visible column. Column choices MUST be stored locally per
browser and restored on later visits. Malformed or stale stored choices MUST
fall back to supported defaults without preventing the dashboard from
rendering. A restore-default action MUST clear customized visibility and width
values.

#### Scenario: Choose visible request-log columns

- **WHEN** an operator selects or deselects columns in the dashboard request-log column chooser
- **THEN** the corresponding request-log headers and cells are shown or hidden
- **AND** the choice is restored when that browser revisits the dashboard

#### Scenario: Preserve a usable table

- **WHEN** only one request-log column remains visible
- **THEN** the dashboard prevents that final column from being hidden

#### Scenario: Recover from invalid stored preferences

- **WHEN** stored request-log preferences are malformed or contain unsupported column identifiers
- **THEN** the dashboard renders with supported default columns and widths

### Requirement: Resizable dashboard request-log columns

The dashboard SHALL render a vertical resize separator at the trailing edge of
each visible request-log header. Dragging a separator MUST adjust that column
within bounded minimum and maximum widths without changing other configured
columns. Individual widths MUST be stored locally per browser and restored on
later visits. Separators MUST support keyboard adjustment, and the table's
minimum width MUST be derived from its visible column widths so overflow
remains horizontally scrollable without a global table-width control.

#### Scenario: Resize a request-log column by dragging

- **WHEN** an operator drags a request-log header separator horizontally
- **THEN** the corresponding header and body column change width
- **AND** the selected width is restored on a later dashboard visit in the same browser

#### Scenario: Resize a request-log column with the keyboard

- **WHEN** a focused request-log header separator receives a Left or Right arrow key
- **THEN** the corresponding column width decreases or increases by the documented step within its bounds

#### Scenario: Wide columns remain reachable

- **WHEN** the sum of visible request-log column widths exceeds the available viewport
- **THEN** the table remains horizontally scrollable
- **AND** no separate global table-width control is displayed

### Requirement: Request logs surface reasoning-token usage

The dashboard request-log API and UI MUST preserve and render the upstream-provided reasoning-token count separately from the inclusive output-token count. The UI MUST treat reasoning tokens as a subset of output tokens and MUST NOT add them to total-token or cost calculations.

#### Scenario: Request row shows an available reasoning count

- **GIVEN** a request-log row has `outputTokens=200` and `reasoningTokens=80`
- **WHEN** the dashboard renders the recent-requests table
- **THEN** the token cell shows 80 reasoning tokens as secondary metadata
- **AND** the row's total-token value remains input tokens plus 200 output tokens

#### Scenario: Request detail identifies the reasoning subset

- **GIVEN** a request-log row has a persisted reasoning-token count
- **WHEN** the operator opens `View Details`
- **THEN** the dialog renders the exact reasoning-token count
- **AND** its label identifies the count as included in output tokens

#### Scenario: Missing reasoning usage is not estimated

- **GIVEN** a request-log row has `reasoningTokens=null`
- **WHEN** the dashboard renders the row and its details
- **THEN** the dashboard does not derive a reasoning count from output text, reasoning summaries, or total output tokens

### Requirement: Reports expose reasoning-token totals

`GET /api/reports` MUST expose the sum of reported reasoning counts as `totalReasoningTokens` in its summary and nullable `reasoningTokens` in each daily row, using the same date, account, model, and user-agent filters as the existing token totals. The summary MUST expose `reasoningUsageKnownRequests`, counting rows whose upstream reasoning count is known, including known zeroes. The reports UI MUST label the aggregate as reported reasoning, show its known-request coverage, render it in the daily breakdown, and export it in the daily CSV. A daily row with requests but no reported reasoning counts MUST preserve `reasoningTokens=null`; known zero MUST remain zero. Existing total-token comparisons MUST remain input tokens plus inclusive output tokens, with a stored reasoning count serving as the output fallback when an older row has no output total.

#### Scenario: Reports aggregate reasoning usage

- **GIVEN** eligible request logs in a report window contain reasoning-token counts of 30 and 70 and one request with an unknown count
- **WHEN** an operator requests that report window
- **THEN** `summary.totalReasoningTokens` is 100
- **AND** `summary.reasoningUsageKnownRequests` is 2
- **AND** each daily row's `reasoningTokens` is the sum for that local-calendar day

#### Scenario: Reports identify reasoning as an output subset

- **GIVEN** a report summary has 1,000 input tokens, 400 output tokens, and 250 reasoning tokens
- **WHEN** the dashboard renders the token summary
- **THEN** the total remains 1,400 tokens
- **AND** the summary identifies 250 reasoning tokens as included in the 400 output tokens

#### Scenario: Daily CSV exports reasoning tokens

- **WHEN** an operator exports the reports daily breakdown
- **THEN** the CSV contains a Reported Reasoning Tokens column
- **AND** every row contains that day's reasoning-token aggregate

#### Scenario: A daily aggregate has no reported reasoning usage

- **GIVEN** a report day contains requests whose reasoning-token counts are all unknown
- **WHEN** the reports API and dashboard render that day
- **THEN** the daily `reasoningTokens` value remains null
- **AND** the table and CSV do not present it as a known zero

#### Scenario: A legacy row has reasoning usage but no output total

- **GIVEN** an eligible request log has `outputTokens=null` and `reasoningTokens=40`
- **WHEN** the report aggregates inclusive output tokens
- **THEN** the row contributes 40 output tokens and 40 reported reasoning tokens
- **AND** reasoning is not added to that output total a second time

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

### Requirement: Routing settings expose inherited capacity overrides

The dashboard routing settings MUST display the effective value and the raw
override state for each of the four account-capacity settings. A `NULL` raw
override MUST render as an empty inheritable input with the effective value
shown as a hint. Clearing that input MUST submit explicit `null`; entering a
nonnegative integer, or an integer from 0 to 100 for the fair-share threshold,
MUST submit an override value. The dashboard MUST prevent invalid values from
being saved and MUST retain the existing stream-recovery-reserve validation.
When validating a clear of a stored override, the dashboard MUST use the
environment baseline value rather than the currently effective override value.

#### Scenario: Inherited capacity is visible

- **GIVEN** a capacity override is `NULL`
- **WHEN** routing settings render
- **THEN** the input is empty
- **AND** the effective environment value is shown as the inherit hint

#### Scenario: Clearing an override round-trips as null

- **GIVEN** a routing setting currently has a numeric override
- **WHEN** the operator empties the field and saves
- **THEN** the update payload contains the field with explicit `null`
- **AND** a subsequent GET shows the effective value and a `null` override

#### Scenario: Unedited fields are preserved

- **GIVEN** one capacity field is cleared and sibling fields have overrides
- **WHEN** the operator saves
- **THEN** the payload does not pin or clear the sibling fields

#### Scenario: Capacity validation remains enforced

- **WHEN** the operator enters a negative value, a non-integer, a fair-share
  value outside 0-100, or a recovery reserve above the effective stream cap
- **THEN** the dashboard prevents the save

#### Scenario: Clearing a stream limit validates against environment capacity

- **GIVEN** a stored stream-limit override of 24, a stored recovery reserve of
  3, and an environment stream limit of 2
- **WHEN** the operator clears only the stream-limit input
- **THEN** the dashboard prevents the save

### Requirement: Settings initial load failure is actionable

The Settings page SHALL render its page-wide loading skeleton only while the
initial settings request is still pending and no settings data is available.

When the initial settings request reaches a terminal error and no settings data
is available, the Settings page MUST NOT render the loading skeleton. It MUST
render the settings error message, MUST announce that error through an alert
semantic, and MUST expose a keyboard-operable, accessibly named Retry action.
When the error carries no message of its own, the page SHALL render a settings
load-failure fallback message. Activating Retry SHALL refetch the settings
detail query without a full page reload, and Retry SHALL be disabled while that
refetch is in flight.

When settings data is available, a settings fetch error SHALL NOT hide the
settings form; the page SHALL keep the form rendered and surface the error
above it.

#### Scenario: Failed initial settings load replaces the skeleton

- **GIVEN** no settings data is available
- **WHEN** the initial settings request reaches a terminal error
- **THEN** the Settings page does not render its loading skeleton
- **AND** the settings error message is rendered and announced through an alert semantic
- **AND** an accessibly named Retry action is available

#### Scenario: Retry refetches settings in place

- **GIVEN** the initial settings request has failed and no settings data is available
- **WHEN** the operator activates Retry
- **THEN** the settings detail query is refetched
- **AND** no full page reload occurs

#### Scenario: Retry is disabled while the refetch is in flight

- **GIVEN** the initial settings request has failed and no settings data is available
- **WHEN** a settings refetch is in flight
- **THEN** the Retry action is disabled

#### Scenario: Pending initial settings load keeps the skeleton

- **GIVEN** no settings data is available and no settings error has occurred
- **WHEN** the initial settings request is still pending
- **THEN** the Settings page renders its loading skeleton
- **AND** no settings error message or Retry action is rendered

#### Scenario: Settings error with cached data keeps the form visible

- **GIVEN** settings data is available
- **WHEN** a settings fetch error is present
- **THEN** the settings form sections remain rendered
- **AND** the settings error message is rendered above them
- **AND** the loading skeleton is not rendered

### Requirement: API key create dialog remains usable in compact viewports

The dashboard API key create dialog MUST constrain its outer shell to the visible viewport. Its title, Close control, and Create action MUST remain fully visible at a 320x568 viewport, and every form field MUST remain reachable through exactly one internal vertical scroll region. The header and footer MUST remain outside that scroll region. The dialog SHALL retain its stacked compact layout, two-column desktop layout, shared Dialog primitive, field behavior, and overlay and Escape dismissal behavior.

#### Scenario: Compact viewport keeps primary controls visible

- **WHEN** an operator opens Create API Key from `/keys` at a 320x568 viewport
- **THEN** the dialog title, Close control, and Create action are fully inside the viewport
- **AND** the dialog shell does not extend above or below the viewport

#### Scenario: Compact form fields use one internal scroller

- **WHEN** the create form fields exceed the height available between the dialog header and footer
- **THEN** all General and Limits fields are reachable through one internal vertical scroll region
- **AND** the dialog header and footer remain outside the scroll region

#### Scenario: Larger compact and desktop layouts remain responsive

- **WHEN** an operator opens Create API Key at 390x844 or a desktop viewport
- **THEN** the dialog remains inside the viewport with its primary controls visible
- **AND** the form is stacked below the desktop breakpoint and uses two columns at the desktop breakpoint

#### Scenario: Existing dismissal behavior is preserved

- **WHEN** an operator presses Escape or activates the dialog overlay while no nested menu surface is active
- **THEN** the create dialog closes through the shared Dialog primitive

### Requirement: Dashboard usage content remains contained on mobile

The dashboard MUST keep the document width within the visible viewport at 320x568 and 390x844. Both usage donut cards, their horizontal content rows, fixed-size charts, and legends MUST remain within the dashboard content width. The request table MAY exceed the viewport width only inside its own horizontal scroller and MUST NOT widen the document. The dashboard SHALL preserve the two-column usage layout and page-level containment at a 1440x900 desktop viewport.

#### Scenario: Usage donuts fit the smallest supported mobile viewport

- **WHEN** an authenticated operator opens `/dashboard` at 320x568 with account usage in both quota windows
- **THEN** the document does not scroll horizontally
- **AND** both usage donut cards and their rendered content remain within the dashboard content width
- **AND** the account-section heading and summary remain within the document width

#### Scenario: Usage donuts fit the larger mobile viewport

- **WHEN** the same dashboard data renders at 390x844
- **THEN** the document does not scroll horizontally
- **AND** both usage donut cards remain within the dashboard content width

#### Scenario: Request table keeps local horizontal scrolling

- **WHEN** the request table's columns require more width than the mobile content area
- **THEN** the table remains wider than its local horizontal scroller
- **AND** the scroller contains that width without widening the document

#### Scenario: Desktop layout remains contained

- **WHEN** the same dashboard data renders at 1440x900
- **THEN** the usage donuts render in two columns
- **AND** the document remains horizontally contained
- **AND** the request table retains its local horizontal scrolling when its columns exceed the available section width

### Requirement: Dashboard request-log filters use symbolic rolling timeframes

For `1h`, `24h`, and `7d`, the dashboard MUST send symbolic `timeframe` to
listing and options and MUST NOT send browser-generated `since`. Selecting
`all` MUST omit both. Refetches MUST preserve all applicable manual filters.

#### Scenario: Browser skew does not alter request-log filters

- **WHEN** the dashboard fetches or refetches `timeframe=24h`
- **THEN** both requests contain `timeframe=24h`
- **AND** neither contains `since`

### Requirement: Background request-log failure preserves retained rows

When a page loaded successfully and a later refresh fails, Request Logs MUST
keep the last successful filters, rows, total, and pagination visible. It MUST
also announce the current failure with a section-local alert and expose Retry.
Error-only rendering remains valid only before any page succeeds.

#### Scenario: Failed refresh retains table

- **GIVEN** a successful request-log page is visible
- **WHEN** a later refresh reaches terminal failure
- **THEN** the table and rows remain visible
- **AND** the section exposes alert and Retry

### Requirement: Dashboard route failures preserve a recoverable shell

The authenticated dashboard SHALL retain its header, main landmark, status
region, and React root when a route is unknown, pending, or fails to render.
Unknown routes MUST render localized Not Found status and a keyboard Dashboard
link. Pending lazy routes MUST render visible loading status. Rejected lazy
imports MUST render an announced error with keyboard reload and Dashboard
actions. Reload MUST fully navigate the current URL so the browser requests the
current asset graph. Route-level code splitting MUST remain intact.

#### Scenario: Unknown route retains shell

- **WHEN** an authenticated operator opens an unknown path
- **THEN** shell landmarks remain rendered
- **AND** Not Found receives focus
- **AND** a keyboard Dashboard link is available

#### Scenario: Pending lazy route is visible

- **WHEN** a matched lazy import remains pending
- **THEN** shell landmarks remain
- **AND** main renders a visible loading status

#### Scenario: Rejected lazy route is contained

- **WHEN** a lazy page import rejects
- **THEN** the React root and shell remain rendered
- **AND** an announced error receives focus
- **AND** keyboard reload and Dashboard actions are available

#### Scenario: Reload retries through current assets

- **WHEN** the operator activates reload after a lazy import rejection
- **THEN** the browser fully navigates the current URL
- **AND** the route renders when its chunk becomes available

### Requirement: Guest request details hide sensitive metadata and archives

The Request Details dialog MUST render full User Agent, Client IP, Conversation ID controls, and the conversation archive panel only for an admin dashboard principal. It MUST omit those fields and MUST NOT mount the archive panel for a guest principal. Request status, model, transport, timing, token, cost, and error details MUST remain available to guests.

#### Scenario: Guest opens request details

- **GIVEN** the authenticated dashboard principal has role `guest`
- **WHEN** the guest opens a request-log detail dialog
- **THEN** the dialog does not render User Agent, Client IP, Conversation ID, or archive controls
- **AND** it continues to render the non-identifying operational request details

#### Scenario: Admin opens request details

- **GIVEN** the authenticated dashboard principal has role `admin`
- **WHEN** the admin opens a request-log detail dialog
- **THEN** the dialog renders the identifying metadata fields when present
- **AND** it mounts the archive panel using `archiveRequestId` with the existing `requestId` fallback

### Requirement: Dashboard conversations query uses a server-authoritative timeframe

The dashboard conversations query (`useConversations`) SHALL request the conversations list by sending the `timeframe` query parameter to `GET /api/conversations` and SHALL NOT synthesize or send a browser-clock-derived `since` timestamp on the polling or refetch path. The query identity (TanStack query key) and the outgoing API parameters for a given `(search, timeframe)` SHALL remain stable across automatic refetches triggered by polling, window focus, or re-mount, so that an unchanged filter selection reuses the same request and the same server-derived window rather than producing a new timestamp on every refetch. Changing the conversation timeframe SHALL trigger a refetch with the newly selected timeframe.

#### Scenario: Conversations polling sends timeframe and omits browser-generated since

- **GIVEN** the dashboard conversations view is mounted with `conversationTimeframe=7d` in the URL
- **WHEN** the 30-second polling refetch fires
- **THEN** the outgoing request to `GET /api/conversations` includes `timeframe=7d`
- **AND** the request does not include any `since` parameter generated from the browser clock

#### Scenario: Refetch reuses the same API parameters for an unchanged timeframe

- **GIVEN** the dashboard conversations view is mounted with `conversationTimeframe=7d` and `search=foo`
- **WHEN** automatic refetches fire multiple times without any filter change
- **THEN** every outgoing request carries the same `timeframe=7d` and `search=foo` parameters
- **AND** the query key for the conversations query does not change between those refetches

#### Scenario: Changing the conversation timeframe triggers a refetch with the new key

- **GIVEN** the dashboard conversations view is mounted with `conversationTimeframe=7d`
- **WHEN** the operator changes the conversation timeframe selector to `30d`
- **THEN** the URL `conversationTimeframe` parameter updates to `30d`
- **AND** the conversations query refetches with `timeframe=30d` under a new query key

#### Scenario: Standalone conversations view also uses server-authoritative timeframe

- **GIVEN** the conversations view is mounted without an injected dashboard state (the standalone mount path)
- **WHEN** the view reads the `conversationTimeframe` parameter from the URL and fetches
- **THEN** the outgoing request sends `timeframe=<key>` and no browser-generated `since`
- **AND** the standalone mount path produces the same server-authoritative behavior as the dashboard-embedded path

#### Scenario: Browser clock skew does not change the conversations request

- **GIVEN** the browser clock is skewed days ahead of or behind the server clock
- **WHEN** the dashboard conversations view fetches or refetches
- **THEN** the outgoing request parameters are unaffected by the browser clock
- **AND** only the `timeframe` parameter (and `search`/`limit`/`offset` when present) is sent

### Requirement: Settings page exposes reset-credit controls

The Settings page SHALL expose a Reset credits section. The section SHALL allow operators to update `show_reset_credit_badges`, `auto_redeem_reset_credits_before_expiry`, and `show_reset_credit_expiry_badge` through the settings API. `show_reset_credit_badges` and `show_reset_credit_expiry_badge` SHALL default to enabled. `auto_redeem_reset_credits_before_expiry` SHALL default to disabled so upgraded deployments preserve the current manual-only redemption behavior. The automatic redemption control SHALL describe that the system attempts to redeem the soonest reset credit about five minutes before it expires. Changes to any of these three settings SHALL be included in the `settings_changed` audit entry's `changed_fields` list.

#### Scenario: Reset-credit display settings save through settings API

- **WHEN** an operator toggles reset-credit badge visibility
- **THEN** the dashboard sends `showResetCreditBadges` through the settings API

#### Scenario: Reset-credit auto redeem setting saves through settings API

- **WHEN** an operator toggles automatic reset-credit redemption
- **THEN** the dashboard sends `autoRedeemResetCreditsBeforeExpiry` through the settings API

### Requirement: Conversation detail URLs preserve opaque identifiers

The dashboard MUST construct conversation detail URLs so stored IDs equal to
`.` or `..` cannot be normalized by the browser into collection or parent
paths. The detail request MUST still resolve to the original conversation ID.

#### Scenario: Dot-only IDs remain detail requests

- **GIVEN** a conversation has the non-empty ID `.` or `..`
- **WHEN** the operator opens its details
- **THEN** the browser requests an opaque detail path
- **AND** the API receives the original dot-only conversation ID

### Requirement: Model-source reasoning metadata editor

The dashboard MUST let operators configure the reasoning metadata stored on
model-source models without assuming one global effort vocabulary.

#### Scenario: Edit arbitrary supported reasoning efforts

- **GIVEN** a model source whose `raw_metadata_json` contains
  `supports_reasoning: true`
- **AND** its `supported_reasoning_levels` include values such as `none` or a
  provider-specific slug
- **WHEN** the dashboard opens the model-source create or edit form
- **THEN** the reasoning controls MUST show those effort slugs without dropping
  or rewriting them
- **AND** saving the form MUST write the edited effort list back into
  `supported_reasoning_levels`.

#### Scenario: Normalize stale defaults during save

- **GIVEN** a model source whose configured default effort is no longer present
  in the edited supported-effort list
- **WHEN** the operator saves the form
- **THEN** the dashboard MUST replace the stale default with one of the
  configured supported efforts
- **AND** it MUST NOT leave `default_reasoning_level` pointing at a removed
  value.

#### Scenario: Seed a first-time reasoning configuration

- **GIVEN** an operator enables reasoning for a model source that previously had
  no configured supported-effort list
- **WHEN** the dashboard reveals the reasoning metadata controls
- **THEN** the form MUST seed an editable default effort list and default value
  so the operator can save a valid initial configuration
- **AND** the operator MUST still be able to replace that seed with arbitrary
  effort slugs before saving.

### Requirement: Provider marks accompany account identities

Dashboard account cards, lists and request-log account cells, and Accounts page lists and detail headings SHALL display a local text-free monochrome provider logo beside the account name. Marks SHALL use consistent sizing, remain visible in light/dark themes and not change privacy, accessible names, truncation or account actions. Unknown or unassigned providers SHALL NOT be mislabeled.

#### Scenario: Mixed provider surfaces
- **WHEN** Codex, Claude and OpenRouter accounts are displayed
- **THEN** each name has its corresponding provider mark on all account identity surfaces
- **AND** Codex accounts use the OpenAI mark, Claude accounts the Claude mark and OpenRouter accounts the OpenRouter mark
- **AND** private text remains blurred without blurring the decorative mark

#### Scenario: Log provenance determines the mark
- **WHEN** an OpenRouter account serves a model made by another vendor
- **THEN** the account cell shows the OpenRouter mark, not the model vendor's mark
- **AND** generic OpenAI-compatible or unassigned rows do not claim a known provider

### Requirement: Request log models use readable names

Request-log model cells SHALL display catalog names when available and readable names for historical or uncatalogued IDs, with the exact technical ID only in the model label's native tooltip. Effort and non-default service tier SHALL appear inline in established muted grey without parentheses; default tier SHALL be omitted from that label. Requested-versus-actual differences, operation labels, filtering, stored IDs and detailed raw metadata SHALL remain unchanged.

#### Scenario: Catalog name and exact ID
- **WHEN** a request uses anthropic/claude-haiku-4-5-20251001 with high reasoning
- **THEN** its visible model label is Claude Haiku 4.5 followed by muted high without parentheses
- **AND** its native tooltip contains anthropic/claude-haiku-4-5-20251001

#### Scenario: Catalog independent rendering
- **WHEN** model catalog loading is incomplete or a historical model is absent
- **THEN** request logs remain visible with readable labels and the exact technical IDs in tooltips

#### Scenario: Standard and non-standard tiers
- **WHEN** a medium-reasoning request reports default service tier
- **THEN** its label shows the model name followed by muted medium and omits default
- **WHEN** that request reports priority service tier
- **THEN** its label also shows muted priority without parentheses

#### Scenario: No reasoning metadata
- **WHEN** a request has no reasoning effort and no non-default service tier
- **THEN** only the model name is shown without empty metadata or dangling punctuation

### Requirement: Dashboard provider cards follow provider order
Dashboard account cards SHALL render Codex accounts first, then Claude accounts, then OpenRouter accounts, each group in its API order.

#### Scenario: Mixed providers
- **WHEN** Codex, Claude and OpenRouter accounts exist
- **THEN** the dashboard renders Codex cards, then Claude cards, then OpenRouter cards

### Requirement: Accounts page exposes the account credit policy
The Accounts page account settings SHALL show a Credits setting for Codex accounts with the choices "Spend credits" and "Never spend credits", plus a hint describing the selected policy's effect. The setting SHALL be hidden for accounts that need re-authentication or are deactivated. Changing it SHALL call the credit-policy endpoint and confirm the change with a toast.

#### Scenario: Reserve an account's credits
- **WHEN** an operator selects "Never spend credits" for an account
- **THEN** the dashboard sends the `never` policy and shows the updated setting

### Requirement: Dashboard request log highlights live arrivals

The dashboard request log SHALL give each row that first appears through a refresh of an unchanged query context (filters, search, timeframe, conversation, page size and page) on the first page a tinted background that fades to the normal row background over a few seconds. Arrival SHALL be determined by log-row identity, so a request that completes after newer requests started is highlighted wherever it is placed, and separate rows sharing a request ID (such as a refused attempt and its retry) are tracked and rendered independently in server order. The initial load, any query-context change and placeholder data shown while a new context loads SHALL establish a new baseline without highlighting. Later pages SHALL NOT highlight rows. Refreshes that only change other dashboard data SHALL NOT interrupt a fade in progress.

#### Scenario: Refresh adds a request
- **WHEN** the first page refreshes and contains a log row that was not on the previous page of the same context
- **THEN** that row starts with a tinted background that fades to the normal background
- **AND** rows that were already shown are not highlighted

#### Scenario: Context change does not highlight
- **WHEN** the operator changes a filter, the search, the page size or the page
- **THEN** no row of the newly loaded result is highlighted

#### Scenario: Later pages do not highlight
- **WHEN** the operator views a page after the first and a refresh shifts new entries onto it
- **THEN** no row is highlighted

#### Scenario: Retried rows share a request ID
- **WHEN** two log rows share a request ID and a refresh prepends a newer row and drops an older one
- **THEN** the table shows exactly the returned rows in server order with no leftover rows

### Requirement: Dashboard quota provider toggle
The dashboard SHALL group the 5-hour, weekly, weekly pace and Top consumers cards in a Quota section with a provider toggle offering Codex and each of Claude and Antigravity that has at least one account. The toggle SHALL switch all four cards together, persist with the dashboard preferences, and be hidden when Codex is the only option. A stored provider without accounts SHALL show Codex. The cards SHALL lay out in four columns on wide screens, two on medium and one on narrow screens.

#### Scenario: No Claude accounts
- **WHEN** no Claude or Antigravity account is configured
- **THEN** the toggle is not shown and the cards show Codex

#### Scenario: Antigravity without Claude
- **WHEN** an Antigravity account exists and no Claude account exists
- **THEN** the toggle offers Codex and Antigravity

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

### Requirement: Request logs and conversations live on the Logs page

The application SHALL serve the request logs and conversations views on a dedicated Logs page at `/logs`, gated by
`dashboard:read`. The Logs page SHALL switch between the two views with a segmented toggle that shows both options at
once and marks the active one, and SHALL keep the active view in the `view` URL parameter (`view=conversations` for
Conversations, absent for Request Logs). The dashboard SHALL NOT render or query request logs or conversations.

#### Scenario: Logs page shows request logs by default

- **WHEN** a user with `dashboard:read` opens `/logs`
- **THEN** the Request Logs view renders with its filters, column layout controls and table

#### Scenario: Segmented toggle switches views

- **GIVEN** a principal with `conversations:read` on the Logs page
- **WHEN** the user activates Conversations in the view toggle
- **THEN** the Conversations view renders and the URL contains `view=conversations`
- **AND** request-log URL parameters are preserved

#### Scenario: Dashboard no longer queries request logs

- **WHEN** a user opens `/dashboard`
- **THEN** no request-log or conversation request is issued
- **AND** the dashboard stat boxes follow the overview timeframe

### Requirement: Settings is organised into section routes

The Settings page SHALL include sections for: routing settings (sticky threads,
reset priority, prompt-cache affinity TTL, weekly pace controls, limit warm-up
controls, and Fast Mode prohibition), password management
(setup/change/remove), TOTP management (setup/disable), API key auth toggle,
API key management (table, create, edit, delete, regenerate), and
sticky-session administration. API key create/edit controls that expose
reasoning effort choices MUST include upstream-supported extended efforts such
as `max` and `ultra`.

Settings SHALL be a layout with a side menu and one child route per section
under `/settings/<section>`. The menu SHALL list the sections in three labelled
groups, in this order: Workspace — General (`general`), Accounts (`accounts`),
Access (`access`), Organisation (`organisation`); Traffic — Routing
(`routing`), Models (`models`), Upstream (`upstream`); Operations — Automations
(`automations`), Data (`data`), Notifications (`notifications`). Each section
SHALL render these cards, in order:

- General: appearance.
- Accounts: import, reset credits, background jobs.
- Access: the Access card (guest access, password, session, TOTP and the People
  tab), API key management, firewall.
- Organisation: company sign-in, reverse-proxy sign-in, sign-in rules, password
  sign-in policy, automatic account management.
- Routing: routing settings, quota phase planner, sticky-session
  administration, cross-account cache isolation probe.
- Models: model catalogue.
- Upstream: upstream proxy administration, resilience, session bridge, upstream
  timeouts.
- Automations: the pause control, automation jobs, recent runs.
- Data: data retention, conversation archive.
- Notifications: quota reset webhook.

Every card SHALL keep its existing permission rule. The Organisation section
SHALL be listed and routable only for sessions holding `security:write`; every
other section SHALL be listed for every session that can open Settings. Opening
`/settings` SHALL navigate to `/settings/general`, opening a section the session
cannot use SHALL navigate to `/settings/general`, and an unknown section SHALL
render the not-found surface. A section's cards SHALL mount, and their data
requests SHALL fire, only while that section is open. The page heading,
subtitle and the read-only, trusted-header and disabled-auth notices SHALL
render above the menu on every section. On narrow viewports the menu SHALL
render as one horizontally scrollable row without group labels, scrolled so
the open section's entry is visible.

#### Scenario: Settings opens on General

- **WHEN** a user opens `/settings`
- **THEN** the SPA navigates to `/settings/general`
- **AND** the side menu marks General as current and the appearance card is visible

#### Scenario: Sections fetch only when opened

- **WHEN** a user opens `/settings/general`
- **THEN** the model catalogue, firewall, quota planner and sticky-session data requests have not been issued
- **AND** opening `/settings/routing` issues the quota planner and sticky-session requests

#### Scenario: Organisation is hidden without security write

- **GIVEN** a session without `security:write`
- **WHEN** the user views the Settings side menu
- **THEN** Organisation is not listed
- **AND** opening `/settings/organisation` navigates to `/settings/general`

#### Scenario: Unknown section

- **WHEN** a user opens `/settings/advanced`
- **THEN** the not-found surface renders

#### Scenario: Phone menu shows the open section

- **GIVEN** a narrow viewport
- **WHEN** a user opens `/settings/upstream`
- **THEN** the Upstream entry is within the visible part of the menu row
- **AND** opening `/settings/access#firewall` still scrolls the page to the firewall card

#### Scenario: API key dialog offers extended reasoning efforts

- **WHEN** an operator opens the API key create or edit dialog
- **THEN** the enforced reasoning control offers `Max` and `Ultra` in addition to existing reasoning efforts

#### Scenario: Save weekly pace gap smoothing window

- **GIVEN** the Routing section is open
- **WHEN** a user selects a weekly pace gap smoothing window from the routing settings card
- **THEN** the app calls `PUT /api/settings` with `weeklyPaceSmoothingMinutes`
- **AND** the saved settings response reflects the selected value

#### Scenario: Save prompt-cache affinity TTL

- **GIVEN** the Routing section is open
- **WHEN** a user updates the prompt-cache affinity TTL from the routing settings card
- **THEN** the app calls `PUT /api/settings` with the updated TTL and reflects the saved value

#### Scenario: Save staggered idle warm-up setting

- **GIVEN** the Routing section is open
- **WHEN** a user toggles staggered idle limit warm-up from the routing settings card
- **THEN** the app calls `PUT /api/settings` with the updated value and reflects the saved value

#### Scenario: Save Fast Mode prohibition

- **GIVEN** the Routing section is open
- **WHEN** a user enables or disables the Fast Mode prohibition control in the routing settings card
- **THEN** the app calls `PUT /api/settings` with `prohibitFastMode`
- **AND** reflects the saved value

#### Scenario: View sticky-session mappings

- **GIVEN** the Routing section is open
- **WHEN** a user views the sticky-session card
- **THEN** the app fetches sticky-session entries and displays each mapping's kind, account, timestamps, and stale/expiry state

#### Scenario: Purge stale prompt-cache mappings

- **GIVEN** the Routing section is open
- **WHEN** a user requests a stale purge from the sticky-session card
- **THEN** the app calls the sticky-session purge API and refreshes the list afterward

### Requirement: Header renders only core destinations

The application header SHALL render exactly the core destinations — Dashboard,
Logs, Reports, Providers, API Keys, and Settings — as top-level navigation items, in
that order, on desktop and in the mobile navigation menu. The header SHALL NOT
render an Advanced menu or any other secondary destination group. A new
destination SHALL be placed as a Settings section or inside an existing page
unless a spec explicitly designates it as core.

#### Scenario: Header shows only core destinations

- **WHEN** a user views the header navigation
- **THEN** Dashboard, Logs, Reports, Providers, API Keys, and Settings render as top-level links
- **AND** no Advanced menu trigger renders

#### Scenario: Retired routes are not found

- **WHEN** a user opens `/automations`, `/firewall`, or `/apis`
- **THEN** the not-found surface renders

#### Scenario: Settings stays active on its sections

- **WHEN** the current route is `/settings/routing`
- **THEN** the Settings navigation item renders in the active state

### Requirement: Route transitions preserve intentional scroll behavior

The dashboard SPA MUST reset the window to the top when a client-side `PUSH` or `REPLACE` navigation changes the final destination pathname and the destination has no hash. The same rule MUST apply to desktop and mobile top-level navigation and to the Settings side menu. The SPA MUST NOT perform that reset for browser-history `POP` navigation, same-path query changes, or destinations with a hash.

#### Scenario: Desktop top-level navigation opens the destination at the top

- **GIVEN** a desktop user has scrolled a dashboard page below its heading
- **WHEN** the user activates a top-level link to a different pathname without a hash
- **THEN** the destination opens with `window.scrollY` equal to `0`
- **AND** the destination heading is visible in the viewport

#### Scenario: Mobile top-level navigation opens the destination at the top

- **GIVEN** a mobile user has scrolled a dashboard page below its heading
- **WHEN** the user opens the header menu and activates a top-level link to a different pathname without a hash
- **THEN** the destination opens with `window.scrollY` equal to `0`
- **AND** the destination heading is visible in the viewport

#### Scenario: Browser history keeps its restoration position

- **GIVEN** the browser has a stored scroll position for an earlier pathname
- **WHEN** the user returns through back or forward history navigation
- **THEN** the route shell does not reset the window scroll position

#### Scenario: Query-only navigation keeps the current position

- **GIVEN** the user is viewing a dashboard pathname at a nonzero scroll position
- **WHEN** an in-app filter or view change updates only that pathname's query string
- **THEN** the route shell does not reset the window scroll position

#### Scenario: Settings card hashes retain target scrolling

- **WHEN** navigation targets `/settings/organisation#organisation-login-policy`
- **THEN** the route shell does not reset the window to the top
- **AND** the section brings the login-policy card into view once its data has loaded

### Requirement: Automations is a Settings section

The SPA MUST render the automations surface at `/settings/automations`: first the
"Pause all automations" control, then the jobs table with its create, edit,
enable/disable, delete and run actions, then recent runs. Opening the section
SHALL request the automation job list from `/api/automations`.

#### Scenario: Open Automations from Settings

- **WHEN** a signed-in user selects Automations in the Settings side menu
- **THEN** the SPA navigates to `/settings/automations`
- **AND** the app requests the automation job list from `/api/automations`

### Requirement: Settings deep links address a section and a card

Links into Settings SHALL use the section route plus an optional card hash. The
Access section SHALL select the People tab for `#people` and the person's own
sign-in controls for `#my-sign-in` and `#totp`, and SHALL scroll to the TOTP
card for `#totp`. The Organisation section SHALL scroll to the company sign-in
card for `#oidc`, the login-policy card for `#organisation-login-policy` and the
automatic account management card for `#organisation-automatic-accounts`, each
after the section's provider, rule and role queries have loaded, and SHALL open
the refused sign-ins sheet for `#organisation-refused`. The header account menu
SHALL link "My two-factor" to `/settings/access#my-sign-in` and "Invite teammate"
to `/settings/access#people`; the `step_up_unavailable` toast action SHALL open
`/settings/access#my-sign-in`; the People tab's sign-in requirements link SHALL
switch to the My sign-in tab. A completed company sign-in test or
re-authentication SHALL return to `/settings/organisation#oidc`.

#### Scenario: Account menu opens the People tab

- **GIVEN** a session holding `users:manage` on a team install
- **WHEN** the user selects "Invite teammate" in the account menu
- **THEN** the SPA opens `/settings/access#people` with the People tab selected

#### Scenario: OIDC return lands on the company sign-in card

- **WHEN** the browser returns to `/settings/organisation#oidc`
- **THEN** the Organisation section renders and scrolls to the company sign-in card after its queries load

### Requirement: Password setup dialog restores invoker focus

The Settings `Set password` setup dialog SHALL retain the exact button that invoked it. When the dialog is dismissed with Escape or its explicit Cancel action, the dialog SHALL restore focus to that connected invoking button without changing the Settings page scroll position. After restoration, `document.body` MUST NOT be the active element.

Focus restoration MUST preserve the password setup flow's authentication request, session refresh, toast, form reset, and conditional mounting behavior. Password change, remove, verify, and TOTP dialogs are outside this requirement.

#### Scenario: Password setup closes with Escape

- **GIVEN** an operator opened password setup from the `Set password` button
- **WHEN** the operator presses Escape
- **THEN** the setup dialog closes without submitting password setup
- **AND** focus returns to that exact `Set password` button without scrolling Settings
- **AND** `document.body` is not active

#### Scenario: Password setup closes explicitly

- **GIVEN** an operator opened password setup from the `Set password` button
- **WHEN** the operator activates Cancel
- **THEN** the setup dialog closes without submitting password setup
- **AND** focus returns to that exact `Set password` button without scrolling Settings
- **AND** `document.body` is not active

### Requirement: Sequential multi-file account import

The Accounts import dialog SHALL accept one or more auth.json files and send them sequentially in selection order through the existing single-file import callback. It SHALL disable selection and submission and prevent dialog dismissal while imports run. The dialog SHALL close and clear selection only after every selected file succeeds. A failure SHALL keep the dialog open, retain the failed and unattempted files for retry, and exclude already successful files from retries. The existing API multipart contract and successful-import refresh behavior SHALL remain unchanged.

#### Scenario: Successful batch

- **WHEN** an operator selects multiple files and submits
- **THEN** each file is imported once in selection order
- **AND** the dialog closes and clears selection after all succeed

#### Scenario: Partial failure and retry

- **WHEN** a later file fails after an earlier file succeeds
- **THEN** subsequent files are not attempted
- **AND** the dialog retains only failed and unattempted files for retry

#### Scenario: In-flight controls

- **WHEN** an import is pending
- **THEN** the file input and submit action remain disabled

### Requirement: Conversation request trace

The authenticated dashboard MUST expose `GET /api/request-logs/conversation-trace` with `conversationId`, `limit`
(1–200, default 50) and `offset`, guarded by conversation read permission. It MUST use the conversation detail
eligible-row scope, order rows by `requested_at` then ID, newest first, and return 404 for an unknown conversation.
Each row MUST expose time, model, effort, request kind and operation, status, error code, latency, first-token
latency, prompt tokens, clamped cache reads, cache writes, output tokens, cache-read ratio, cache event and idle gap.
It MUST NOT expose account identity.

A row whose prompt exceeds its cache reads by more than 20,000 tokens SHALL carry the first matching event, compared
with the previous row that carries a prompt: `first` without one; `compaction` when either is a compaction;
`model_switch`; `account_switch` when account or model source differs; `idle_expiry` when the row has a known
cache lifetime and the gap from the previous request's end exceeds it; `bust` when reads are below 10% of the
previous prompt and the prompt is 0.95–1.2 times it; `growth` when reads are at least 90% of it; otherwise `miss`.
Only Claude rows have a known lifetime: 5 minutes, or 1 hour when the row wrote to the 1-hour cache. Codex account
rows MUST NOT be classified as `idle_expiry`, because signed-in Codex accounts retain their cache indefinitely; other
model sources report no lifetime. The previous row of a page's oldest row MUST be loaded so classification does not
depend on pagination.

Conversation Details SHALL show the trace below the model table as a timeline: elapsed-time bar relative to the
longest loaded request, coloured by cache-read share (at least 80%, at least 30%, below, unmeasured), event tag with
its explanation, error code for failed rows, and a control to load further pages.

#### Scenario: A conversation resumes after its cache expired
- **WHEN** a Claude request follows the previous one by 10 minutes on the same model and source and reads none of its
  120K-token prompt from the 5-minute cache
- **THEN** its trace row carries `idle_expiry` with the idle gap
- **AND** Conversation Details shows it with the low cache band and an "idle expiry" tag

#### Scenario: A Codex conversation resumes cold after a break
- **WHEN** a Codex request follows the previous one by 3 hours on the same model and account and reads none of its
  similarly sized prompt
- **THEN** its trace row carries `bust`, not `idle_expiry`

#### Scenario: Paging the trace
- **WHEN** a conversation has more rows than one page
- **THEN** the first page holds the newest rows and `hasMore` is true
- **AND** the oldest row on the page is classified against the newest older row

#### Scenario: Guests cannot read the trace
- **WHEN** a dashboard user without conversation read permission requests the trace
- **THEN** the response is 403

### Requirement: Distinct request-log plan tag colors

Request-log plan badges MUST assign distinct colors to `free`, `plus`, `prolite`, `pro`, `team`, `business`, `enterprise`, `edu`, `max`, `max_5x`, and `max_20x` in both light and dark themes. The same plan key MUST use the same palette across providers while preserving provider-specific labels. The recognized rate-limit metadata keys `guest`, `go`, `free_workspace`, `education`, `quorum`, and `k12` MUST also have explicit distinct colors when displayed. Badge text MUST have at least 4.5:1 contrast against its background in normal and hovered states in both themes.

#### Scenario: Previously aliased tiers appear together
- **WHEN** Pro, Max, Max 5×, Max 20×, Team, and Enterprise appear in a request table
- **THEN** each tier has its own text, background, and border colors
- **AND** the colors remain distinct when the dashboard theme changes

#### Scenario: Unknown tiers are not presented as Free
- **WHEN** a request snapshot contains `unknown` or an unrecognized nonempty plan key
- **THEN** its existing label is retained with neutral colors distinct from Free

#### Scenario: Missing snapshots remain missing
- **WHEN** a request has a null or blank plan snapshot
- **THEN** its plan cell displays `--` without a plan badge

#### Scenario: Same key across providers
- **WHEN** Codex Pro and Claude Pro requests appear together
- **THEN** their plan badges use identical theme colors
- **AND** each retains its existing display label

### Requirement: Account notes
Every account on the Accounts page SHALL support an optional operator note of at
most 2,000 characters: Codex accounts and every model-source account (Claude,
Antigravity, OpenRouter and OpenAI-compatible). Notes SHALL be stored with the
account, listed by `GET /api/account-notes` for readers of accounts, and set by
`PUT /api/account-notes/accounts/{account_id}` or
`PUT /api/account-notes/model-sources/{source_id}` for account writers. A note
that is empty after trimming SHALL be stored as no note. Each account detail SHALL
show a Note panel under its header and status alerts with the note's text and line breaks;
writers SHALL be able to edit and save or cancel it, and read-only users SHALL see
it without edit controls. Notes SHALL NOT affect routing.

#### Scenario: Save a note
- **WHEN** a writer saves "Reserved for CI" on a Claude account
- **THEN** the Claude account detail shows "Reserved for CI" after reload

#### Scenario: Clear a note
- **WHEN** a writer saves a note containing only whitespace
- **THEN** the account has no note and its Note panel shows the empty state

#### Scenario: Read-only user
- **WHEN** a read-only user opens an account with a note
- **THEN** the note is visible without an edit control

#### Scenario: Unknown account
- **WHEN** a note is set for an account ID that does not exist
- **THEN** the API returns 404 `account_not_found`

### Requirement: Provider sign-in and import dialogs share one flow

Claude and Antigravity sign-in SHALL use the Codex browser sign-in stages: a details stage, an
authorization stage with the authorization URL, Copy, Refresh link (which starts a new flow), a
plain-text monospace paste field with Submit, and a waiting line with an expiry countdown, followed
by a success or error stage with Try again. The URL box, copy button and paste field SHALL be shared
with the Codex dialog. Credential file import SHALL be a separate dialog per provider using one
shared file area, which the Codex multi-file import uses as well.

#### Scenario: Refresh the authorization link

- **WHEN** an operator presses Refresh link during Claude sign-in
- **THEN** a new authorization flow starts and its URL replaces the previous one

#### Scenario: Sign-in fails

- **WHEN** completing an Antigravity sign-in fails
- **THEN** the dialog shows the error stage with Close and Try again

### Requirement: Provider accounts re-authenticate like Codex

Claude and Antigravity account details SHALL offer a "Re-authenticate" control with the Codex label
and icon, opening a menu with "Sign in again" and "Import credential file". Re-authentication dialogs
SHALL show the saved identity read-only instead of a name field. When a Claude re-authentication is
held for an identity mismatch, a confirmation dialog SHALL compare the saved and incoming email,
organization and plan; Cancel SHALL discard the held sign-in and "Replace saved identity" SHALL
confirm it. A matching sign-in SHALL complete without confirmation.

#### Scenario: Plan change moves the organization

- **WHEN** a Claude sign-in for the same email returns a different organization
- **THEN** the confirmation dialog highlights the organization and plan rows, and confirming completes the reconnect without another sign-in

#### Scenario: Cancel the replacement

- **WHEN** the operator cancels the confirmation
- **THEN** the held sign-in is discarded and the saved credentials stay unchanged

### Requirement: Account subscription end date
Codex, Claude and Antigravity accounts SHALL support an optional subscription
end, a date and time stored in UTC. `GET /api/account-subscriptions` SHALL list
the set end dates for readers of accounts, and
`PUT /api/account-subscriptions/accounts/{account_id}` or
`PUT /api/account-subscriptions/model-sources/{source_id}` SHALL set or clear
one for account writers. A timezone-less end SHALL be rejected. Setting an end on
an OpenRouter or OpenAI-compatible account SHALL fail with
`subscription_end_not_applicable`. The Codex, Claude and Antigravity account
details SHALL show a Subscription end panel after the Note panel, stating the
end in the dashboard's date format with the time remaining, or that it has
passed and is ignored by projections; writers SHALL be able to set it in local
time, change it or clear it. The end date SHALL only inform projections: it
SHALL NOT change the account's status or affect routing, before or after it passes.

#### Scenario: Set an end date
- **WHEN** a writer sets 15 November 2026 18:00 local time on a Claude account
- **THEN** the account stores that instant in UTC and its detail shows it with the time remaining

#### Scenario: Clear an end date
- **WHEN** a writer clears the end date
- **THEN** the account has no end date and projections treat it as renewing

#### Scenario: Not applicable
- **WHEN** an end date is set on an OpenRouter account
- **THEN** the API returns 400 `subscription_end_not_applicable`

#### Scenario: Unknown account
- **WHEN** an end date is set for an account ID that does not exist
- **THEN** the API returns 404 `account_not_found`

### Requirement: Quota projections honor subscription end dates
The weekly pace for Codex, Claude and every Antigravity family SHALL treat an
account's upcoming subscription end as a capacity cutoff. An end that has
passed SHALL be ignored, so the account is projected as renewing:

- When the end comes before the account's next weekly reset, its expected
  remaining and scheduled burn SHALL follow a linear schedule from the window
  start to the end, so the plan spends the account by its end.
- Resets at or after the end SHALL NOT count as relief, as reset events, or as
  refills in the forecast simulation; at the end the account's remaining
  balance SHALL be removed from the pool.
- The forecast and the depletion ETA SHALL spend the balance that expires
  first, by reset or end, before later balances.
- When no pooled account resets before its end, there SHALL be no next relief,
  and a depletion ETA SHALL make the verdict `runs_dry`.
- The add-capacity estimate SHALL count each account's capacity only for the
  share of the next seven days before its end.
- The response SHALL list each end within the next seven days with the
  account's weekly capacity, and the runway timeline SHALL mark it distinctly
  from resets.

The Codex 5-hour and weekly depletion projections SHALL use the end as the
window's horizon when it precedes the reset, measuring the safe line from the
window start to the end.

#### Scenario: Ending account brings no relief
- **GIVEN** a Codex account at 100% weekly usage whose subscription ends a day before its reset
- **WHEN** the weekly pace is computed
- **THEN** that reset is neither the next relief nor a reset event, and an end marker is listed instead

#### Scenario: Remaining quota lapses at the end
- **GIVEN** two accounts with equal remaining quota, one ending in 10 hours
- **WHEN** the depletion ETA is computed at a burn rate that spends half of one account's remaining quota in 10 hours
- **THEN** the ending account's balance is spent first and its unspent half is removed at the end, shortening the ETA compared with no end date

#### Scenario: Passed end is ignored
- **WHEN** an account's subscription end has passed and the account keeps serving requests
- **THEN** the account's status and routing are unchanged
- **AND** the weekly pace and depletion project it as a renewing account

#### Scenario: No end dates
- **WHEN** no account has an end date
- **THEN** every projection equals the projection without the feature

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

### Requirement: API Keys page address and title

The page that manages downstream API keys SHALL be served at `/keys` and SHALL be titled "API Keys" in its heading
and header navigation item. The application SHALL NOT route or redirect `/apis`.

#### Scenario: API Keys page opens at its address

- **WHEN** a user opens `/keys`
- **THEN** the API Keys page renders with the heading "API Keys"
- **AND** the API Keys navigation item renders in the active state

#### Scenario: The former address is not redirected

- **WHEN** a user opens `/apis`
- **THEN** the not-found surface renders and the address stays `/apis`

### Requirement: API Keys table

`/keys` SHALL show a header with the page title, the number of keys, the number of active keys, the 7-day cost and
the lifetime cost of all keys, and a Create key action for operators who may write. Below it SHALL follow the API-key
comparison chart and one table of all keys. Each row SHALL show the key's name, prefix and scope (models, accounts and
a non-foreground traffic class), its status, its first two limit meters with "+N more" for further rules, its last 7
days (a sparkline, cost and tokens from the comparison trends), its lifetime cost, share and requests, its last use,
and a menu with Open, Open in Logs, Copy prefix and, for operators who may write, Regenerate and Disable or Enable.
Activating a row SHALL open `/keys/:keyId`. The table SHALL offer search by name or prefix, an All / Active / Needs
attention / Disabled & expired filter with counts, and sorting by last used, 7-day cost, lifetime cost, name or expiry.

A key's status SHALL be Disabled when it is inactive, Expired when its expiry has passed, Limit reached when any limit
rule's current value has reached its maximum, Expiring when it expires within 14 days, and Active otherwise. Needs
attention SHALL contain Limit reached and Expiring keys; Active SHALL contain Active and Expiring keys.

#### Scenario: Limit reached

- **WHEN** an active key has a weekly cost rule at 150 of 150
- **THEN** its row shows Limit reached
- **AND** the Needs attention filter includes it

#### Scenario: Open a key

- **WHEN** an operator activates a key's row
- **THEN** the page navigates to `/keys/<keyId>`

#### Scenario: Read-only sessions

- **WHEN** a session that may read but not write keys opens `/keys`
- **THEN** the Create key action and the row menu's Regenerate and Disable entries are absent

### Requirement: API key page

`/keys/:keyId` SHALL show the key in the frame of a provider account page: a sticky, collapsible rail of all keys with
search and arrow-key navigation, a breadcrumb that becomes a key switcher on narrow screens, a header with the key's
name, status, prefix, creation, last use and expiry, the actions Open in Logs, Regenerate and Disable or Enable, and a
⋯ menu with Copy prefix, Copy key ID and Delete. A banner SHALL explain a Limit reached, Expiring, Disabled or Expired
key with a matching action. Overview and Settings tabs SHALL be addressed by `/keys/:keyId` and
`/keys/:keyId/settings`, and the rail and switcher SHALL keep the open tab. An unknown ID SHALL show "API key not
found" with a link to all keys. Read-only sessions SHALL see no write actions and no Settings tab.

#### Scenario: Switch keys on the Settings tab

- **WHEN** an operator on `/keys/a/settings` selects key `b` in the rail
- **THEN** the page shows `/keys/b/settings`

#### Scenario: Unknown key

- **WHEN** a user opens `/keys/missing`
- **THEN** the page shows "API key not found"

### Requirement: API key Overview tab

The Overview tab SHALL show a Last 7 days card with the key's requests, tokens with cached tokens, estimated cost and
last use, and one chart that shows cost and tokens together with a Per hour / Cumulative control. Beside it SHALL
follow cards for cost by account over the last 7 days as bars with provider logos and account colours, the key's limits
with current value, maximum, percentage and reset time, the pooled 5h and weekly capacity remaining when available,
the access rules in force, and lifetime usage. Edit links on the Limits and Access cards SHALL open the Settings tab
for operators who may write. Deleted accounts SHALL be labeled "Deleted Account", unattributed usage "Unknown Account",
and account names SHALL follow the privacy setting.

#### Scenario: Cost and tokens in one chart

- **WHEN** a key has hourly usage in the last 7 days
- **THEN** its Overview chart shows cost and tokens together
- **AND** Cumulative shows both as running totals

### Requirement: API key Settings tab

The Settings tab SHALL hold every field of the former edit dialog as full-width cards: General (name, expiry, traffic
class), Models and reasoning (allowed models, apply to Codex /model, enforced model, allowed efforts, enforced effort,
enforced service tier), Routing (assigned accounts, assigned model sources, HTTP client routing), Limits (rule editor,
each rule's current usage and a Reset usage action that confirms before sending `resetUsage`), and Client usage display
(usage sections), followed by a card with Regenerate, Disable or Enable, and Delete. One save bar SHALL show the
number of unsaved changes with Discard and Save changes, and SHALL send only the changed fields. Settings › Access SHALL
open a key's Settings tab to edit it.

An account-scoped key whose assigned accounts were all deleted stays scoped and can use no account. The Settings tab
SHALL explain this and SHALL send an empty account list only when the operator explicitly removes the restriction;
saving unrelated changes SHALL NOT broaden the key to every account.

#### Scenario: Save one change

- **WHEN** an operator renames a key and saves
- **THEN** the save bar disappears and the key shows the new name

#### Scenario: Deleted accounts keep the key denied

- **WHEN** an account-scoped key has no remaining assigned accounts
- **AND** the operator renames it and saves without removing the restriction
- **THEN** the dashboard does not send `assignedAccountIds`

#### Scenario: Explicitly remove a dead account scope

- **WHEN** an account-scoped key has no remaining assigned accounts
- **AND** the operator checks "Remove account restriction" and saves
- **THEN** the dashboard sends `assignedAccountIds=[]`

#### Scenario: Discard

- **WHEN** an operator changes a field and selects Discard
- **THEN** every field shows its saved value again

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
