## ADDED Requirements

### Requirement: Independent dashboard model editing
The dashboard SHALL separate source connection settings from per-model settings in source creation and editing. Each model SHALL have independently editable ID, display name, enabled state, context and output limits, capabilities, reasoning efforts and token/audio pricing. Editing one model MUST NOT change another model or unrelated raw metadata. Blank prices SHALL represent unknown pricing and zero SHALL represent a free rate. Invalid numeric values and duplicate or empty model IDs MUST prevent submission.

#### Scenario: Edit one model price
- **GIVEN** a source with two differently configured models
- **WHEN** an operator changes one model's output price and saves
- **THEN** only that model's output price changes and the other model retains all its settings

#### Scenario: Manage models
- **WHEN** an operator adds, removes or disables a model and saves
- **THEN** the submitted model list reflects those edits without losing other model settings

#### Scenario: Invalid model fields
- **WHEN** a model has a negative price, nonintegral limit, empty ID or duplicate ID
- **THEN** the dashboard prevents submission and displays an actionable validation message

#### Scenario: Source summary pricing
- **WHEN** a source contains models with different prices
- **THEN** the dashboard lists each model's own input, cached-input and output rates with USD per million token units
- **AND** missing rates are not displayed as zero

#### Scenario: Cancelled edits
- **WHEN** an operator closes an unsaved create or edit dialog and reopens it
- **THEN** unsaved changes are discarded
