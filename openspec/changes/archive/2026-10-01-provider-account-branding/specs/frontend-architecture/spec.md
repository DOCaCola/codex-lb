## ADDED Requirements

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

Request-log model cells SHALL display catalog names when available and readable names for historical or uncatalogued model IDs. The exact technical model ID SHALL appear only in the native browser tooltip of the model label. Reasoning effort, service tier, operation labels, filtering and stored IDs SHALL remain unchanged.

#### Scenario: Catalog name and exact ID
- **WHEN** a request uses anthropic/claude-haiku-4-5-20251001 with high reasoning
- **THEN** its visible model label is Claude Haiku 4.5 (high)
- **AND** its native tooltip contains anthropic/claude-haiku-4-5-20251001

#### Scenario: Catalog independent rendering
- **WHEN** model catalog loading is incomplete or a historical model is absent
- **THEN** request logs remain visible with readable labels and the exact technical IDs in tooltips
