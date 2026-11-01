## ADDED Requirements

### Requirement: Top-level pages share one title row

Dashboard, Logs, Reports, Providers, API Keys and Settings SHALL each start with the same title row: the page title
as the level-one heading in one size and weight, optional page controls right after it, optional short muted context,
and page actions aligned to the right edge. The row SHALL sit above the page content, outside any card, and SHALL NOT
carry an icon or a subtitle. Pages whose first toolbar row holds page controls SHALL place those controls in the title
row, so the title adds no height of its own. Account and key detail views keep their breadcrumb in place of the row.

#### Scenario: Same title on every page
- **WHEN** an operator opens Dashboard, Logs, Reports, Providers, API Keys or Settings
- **THEN** each page starts with its title in the same size and weight, outside any card

#### Scenario: Context and actions share the row
- **WHEN** an operator opens API Keys
- **THEN** the key summary follows the title and the Create key action sits at the right end of the same row

#### Scenario: Toolbar controls share the row
- **WHEN** an operator opens Logs
- **THEN** the view switch, time range and refresh follow the title, and the summary and pager sit at the right end
  of the same row

## MODIFIED Requirements

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
requests SHALL fire, only while that section is open. The page title row and
the read-only, trusted-header and disabled-auth notices SHALL
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

### Requirement: Logs page keeps navigation in view

The Logs page SHALL start with the shared page title row holding the view switch, the active view's time range,
refresh, a one-line summary and a compact pager (range, previous and next). In the Request Logs view one filter card
below it SHALL hold the search, filters, conversation badge, reset and column controls; the Conversations view has no
filter card. The summary SHALL show the filtered request count with its short cost, the full cost coverage on hover,
or the conversation count.

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

### Requirement: Reports toolbar

The `/reports` page MUST start with a toolbar that stays pinned below the navigation while scrolling and MUST NOT
render a subtitle. Its first row MUST be the shared page title row and MUST
contain the `7d`, `30d`, `90d` and `Custom` range presets, the selected range as a readable label, the comparison
window, the time the report was generated and a refresh action. Start and end date inputs MUST be shown while
`Custom` is active. A filter card below it MUST contain multi-select `Accounts`, `API keys`, `Models` and `User agents`
filters, a `Reset` action shown while any filter is active, and a `Sections` menu.

#### Scenario: Toolbar replaces title and filter card
- **WHEN** an authenticated operator opens `/reports`
- **THEN** the page shows its title row and then the toolbar card
- **AND** the default `7d` preset is highlighted and its range and comparison window are shown

#### Scenario: Custom range shows date inputs
- **WHEN** the operator activates `Custom`
- **THEN** start and end date inputs are shown with the current range

#### Scenario: Refresh refetches the report
- **WHEN** the operator activates refresh
- **THEN** the report and options queries refetch and the generation time updates


### Requirement: Settings page renders in the active locale

The Settings page and its constituent sections (`Appearance`, `Routing`, `Import`, `Session`, `Password`, `TOTP`) SHALL render all user-visible strings — page title, section headings and descriptions, switch and select labels, button labels, dialog titles and descriptions, validation messages, warning banners, and toast messages — through the active i18n locale. Selecting `zh-CN` MUST translate the entire surface above to Simplified Chinese, with the explicit exceptions of the embedded `ApiKeysSection`, `FirewallSection`, `QuotaPlannerSection`, `StickySessionsSection`, and `UpstreamProxySettings` rendered inside Settings, which belong to other capabilities and remain English until their own migrations.

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

