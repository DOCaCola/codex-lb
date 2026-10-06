## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Header navigation progressive disclosure

The application header SHALL render core destinations — Dashboard, Logs, Reports,
Accounts, APIs, and Settings — as top-level navigation items, in that order. Non-core
destinations (currently Automations) SHALL NOT render as top-level items: on
desktop they SHALL be reachable through an Advanced menu that opens in one
interaction, and in the mobile navigation menu they SHALL be grouped under an
Advanced label. Direct routes to non-core destinations (e.g. `/automations`)
SHALL continue to resolve, and the legacy `/firewall` route SHALL continue to
redirect to `/settings`. A new page-level navigation destination SHALL default
to the Advanced menu unless a spec explicitly designates it as core.

#### Scenario: Advanced menu reveals Automations

- **WHEN** a user opens the Advanced menu in the header
- **THEN** an Automations item is revealed
- **AND** activating it navigates to `/automations`

#### Scenario: Automations is not a top-level item

- **WHEN** a user views the header navigation
- **THEN** Dashboard, Logs, Reports, Accounts, APIs, and Settings render as top-level links
- **AND** Automations does not render as a top-level link

#### Scenario: Advanced trigger reflects the active route

- **WHEN** the current route is an advanced destination such as `/automations`
- **THEN** the Advanced menu trigger renders in the active state
- **AND** on core routes it renders in the inactive state

#### Scenario: Deep links to advanced destinations keep working

- **WHEN** a user opens `/automations` directly
- **THEN** the Automations page renders

#### Scenario: Legacy firewall route redirects

- **WHEN** a user opens `/firewall`
- **THEN** the app redirects to `/settings`

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

## RENAMED Requirements

- FROM: `### Requirement: Guest dashboard hides the Conversations view`
- TO: `### Requirement: Logs page hides the Conversations view without conversation access`
