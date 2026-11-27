## ADDED Requirements

### Requirement: Model catalogue edits names and context windows

Each Settings model catalogue row SHALL have an Edit action opening an inline editor for name and context window, with
"Use provider name" and "Use default" (or "Use environment value") resets, Enter to save and Escape to cancel. A name
equal to the provider name SHALL remove the stored name. Image models and redirect sources SHALL show a note instead
of the window input. Provider account dialogs and the model-source editor SHALL NOT offer name fields.

#### Scenario: Renaming a model
- **WHEN** an operator edits `openrouter/z-ai/glm-5.3-flash`, enters "GLM Flash" and presses Enter
- **THEN** the row shows "GLM Flash" with the provider name beneath it

#### Scenario: Image model
- **WHEN** an operator edits an image model
- **THEN** only the name can be changed

#### Scenario: Read-only user
- **WHEN** a read-only user opens the model catalogue
- **THEN** every Edit action is disabled

### Requirement: Model catalogue search and provider filter

The Settings model catalogue SHALL offer a search box matching slug and name and a provider filter. Renamed rows SHALL
show the provider's name beneath the operator's name.

#### Scenario: Searching by provider name
- **GIVEN** `openrouter/z-ai/glm-5.3-flash` is renamed "GLM Flash"
- **WHEN** the operator selects the OpenRouter filter and searches "glm"
- **THEN** only matching OpenRouter rows remain
