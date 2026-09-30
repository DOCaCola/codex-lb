## REMOVED Requirements

### Requirement: Account card row height is 11.5rem

**Reason**: A fixed-row capped viewport does not match the full, content-driven provider grid and can truncate provider metrics or actions.
**Migration**: No configuration change. Render all cards using intrinsic grid sizing without a height cap or inner scrolling.

## ADDED Requirements

### Requirement: Dashboard provider cards share one presentation layout

Codex, Claude and OpenRouter dashboard cards SHALL reuse one shared identity/status header, provider-content body and bottom action footer with consistent spacing and typography. Optional identity descriptions SHALL NOT shift the common body start within a row. Provider units, unknown/stale observations, privacy behavior and existing action permissions SHALL be preserved without fabricating unsupported metrics. Codex and Claude card quota windows SHALL use the same one-column or two-column arrangement on desktop and mobile; detail and list layouts SHALL retain their existing responsive behavior.

#### Scenario: Mixed providers retain their semantics
- **WHEN** Codex, Claude and OpenRouter cards appear together
- **THEN** they share the header/body/footer layout
- **AND** quota percentages, dollar balances, privacy and existing actions retain their provider-specific meanings

#### Scenario: Optional email does not shift quotas
- **WHEN** one Codex card has an additional email description and another provider card does not
- **THEN** their shared body sections begin at the same vertical position within that row

#### Scenario: Card quotas remain consistent on mobile
- **WHEN** Codex and Claude cards each have two quota windows at a narrow viewport
- **THEN** both render two quota columns without horizontal document overflow

### Requirement: Dashboard account grid uses intrinsic equal-height cards

Every provider card SHALL use the same flexible grid-item wrapper. Multi-column account grids SHALL use equal content-driven card heights across rows and align action footers along the bottom of each row. Single-column layouts SHALL retain natural card heights. Cards SHALL show their content in full without a fixed height cap, clipping or inner scrolling. Grid items and cards SHALL remain within their allocated column width.

#### Scenario: Different provider content stays aligned
- **WHEN** multi-column cards have different amounts of provider content or identity lines
- **THEN** all visible card surfaces have equal heights determined by the tallest content
- **AND** footers in the same row have matching bottom alignment

#### Scenario: Mobile retains full natural content
- **WHEN** the account grid uses a single column
- **THEN** cards use natural content heights and all metrics and actions remain contained and accessible
