## ADDED Requirements

### Requirement: Model catalogue controls client list visibility

The Settings model catalogue SHALL show a "Client lists" switch per model that hides or lists it and saves immediately. Rows SHALL be grouped by provider, hidden rows dimmed, and an All / Listed / Hidden filter with counts SHALL narrow the table. The card SHALL state that hidden models stay usable by name and that changing the listed models resets each open conversation's prompt cache once.

#### Scenario: Operator hides a model
- **WHEN** an operator turns off the switch for `gpt-5.6-sol`
- **THEN** the row shows "Hidden" and is dimmed
- **AND** the Hidden filter count increases by one

#### Scenario: Read-only user
- **WHEN** a read-only user opens the model catalogue
- **THEN** every "Client lists" switch is disabled

### Requirement: Compaction route pickers mark hidden models

Compaction route model pickers SHALL keep offering hidden models and mark them as hidden.

#### Scenario: Hidden model in a compaction route
- **GIVEN** `gpt-6-sol` is hidden
- **WHEN** an operator opens a compaction route's model picker
- **THEN** `gpt-6-sol` is offered and marked as hidden
