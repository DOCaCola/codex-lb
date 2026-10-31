## MODIFIED Requirements

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

## ADDED Requirements

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
