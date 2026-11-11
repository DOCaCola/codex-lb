## ADDED Requirements

### Requirement: Provider account pages share one Refresh action

Every provider account page (Codex, Claude, Antigravity, OpenRouter) SHALL show a header action labelled "Refresh" with the same icon, size and placement next to the pause control. It SHALL fetch that account's current provider data immediately without a model request. Read-only users SHALL see it disabled.

#### Scenario: Same action on every provider
- **WHEN** an operator opens any provider account page
- **THEN** the header shows a "Refresh" action
- **AND** no provider shows "Check limits", "Refresh balance" or "Force probe" in its header

#### Scenario: Codex account that cannot refresh
- **WHEN** a Codex account requires re-authentication or is deactivated
- **THEN** its Refresh action is disabled
