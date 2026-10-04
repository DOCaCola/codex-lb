## ADDED Requirements

### Requirement: Account chart colour resolution
Every live Codex account and model source SHALL have one resolved chart colour, an index into the twelve-colour
chart palette. An explicitly chosen colour MUST win. Accounts without a choice SHALL take, in creation order, the
first palette index not claimed by any choice, cycling through the palette once every index is in use. Deleted
accounts MUST NOT take part. Each account SHALL also report the colour it would receive without its choice.

#### Scenario: Explicit choice
- **WHEN** an account has a chosen colour
- **THEN** that colour is its resolved colour, even if another account chose the same colour

#### Scenario: Automatic assignment
- **WHEN** accounts have no chosen colour
- **THEN** they receive unclaimed palette indices in creation order

### Requirement: Account colour management
The dashboard SHALL list resolved account colours for users who can read accounts and SHALL let users who can
write accounts set or clear a Codex account's or model source's colour. Unknown targets MUST be rejected as not
found. Account detail headings SHALL show the current colour as a button that opens a palette popover with an
Automatic option and marks colours explicitly chosen for other accounts; automatically assigned colours MUST NOT be
marked.

#### Scenario: Choosing a colour
- **WHEN** a user picks a palette colour in the popover
- **THEN** the choice is stored and every chart and logo for that account updates

#### Scenario: Returning to automatic
- **WHEN** a user chooses Automatic
- **THEN** the stored choice is cleared and the account takes its automatic colour

### Requirement: Consistent account colours in charts
Dashboard remaining-quota donuts, dashboard account cards and list rows, the request log, the Accounts page list and
detail headings, and the API-key cost donut SHALL use each account's resolved colour, and provider logos SHALL be
painted in it. API-key cost entries SHALL carry the resolved
colour so the cost chart does not require account read access. Entries for deleted accounts SHALL remain grey, and
entries without a known account SHALL use a palette colour not shown in that chart.

#### Scenario: Same colour across charts
- **WHEN** an account appears in a dashboard donut and the API-key cost donut
- **THEN** both show it in the same colour, matching its logo
