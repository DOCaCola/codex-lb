## REMOVED Requirements

### Requirement: Settings page
**Reason**: The single page with collapsed Advanced and Organisation groups is replaced by section routes; its controls continue under "Settings is organised into section routes".
**Migration**: Every card is in one Settings section; see the placement table in the requirement that replaces it.

### Requirement: Header navigation progressive disclosure
**Reason**: The header no longer has an Advanced menu; its only entry (Automations) is a Settings section. Continues as "Header renders only core destinations".
**Migration**: Open Settings → Automations (`/settings/automations`).

### Requirement: Dashboard route transitions preserve intentional scroll behavior
**Reason**: The `/firewall` compatibility redirect it special-cased is retired. Continues as "Route transitions preserve intentional scroll behavior".
**Migration**: None.

### Requirement: Automations page is available from top-level navigation
**Reason**: Automations is a Settings section; the header no longer has an entry for it.
**Migration**: Open Settings → Automations (`/settings/automations`).

### Requirement: Legacy firewall route expands Advanced and targets the firewall section
**Reason**: The Advanced group no longer exists and no legacy redirects are kept.
**Migration**: The firewall card is in Settings → Access (`/settings/access`).

## ADDED Requirements

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
- Models: model sources, model catalogue.
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
- **THEN** the model sources, firewall, quota planner and sticky-session data requests have not been issued
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
Logs, Reports, Accounts, APIs, and Settings — as top-level navigation items, in
that order, on desktop and in the mobile navigation menu. The header SHALL NOT
render an Advanced menu or any other secondary destination group. A new
destination SHALL be placed as a Settings section or inside an existing page
unless a spec explicitly designates it as core.

#### Scenario: Header shows only core destinations

- **WHEN** a user views the header navigation
- **THEN** Dashboard, Logs, Reports, Accounts, APIs, and Settings render as top-level links
- **AND** no Advanced menu trigger renders

#### Scenario: Retired routes are not found

- **WHEN** a user opens `/automations` or `/firewall`
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
