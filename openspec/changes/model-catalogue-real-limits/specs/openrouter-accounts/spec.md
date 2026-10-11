## MODIFIED Requirements

### Requirement: Synchronized model selection
The system SHALL synchronize the authenticated model catalog on creation, periodically and on manual refresh. It MUST preserve explicit selections and display names, mark removed models unavailable, and retain the last successful snapshot on synchronization failure. Selected mode SHALL keep new models disabled and advertise/route only selected available models. Explicit all-model mode SHALL advertise/route all eligible conversation models while retaining curated choices and keeping image selections explicit. Context and output limits MUST follow the provider catalog, using `top_provider` limits when they are stricter; selections MUST NOT carry context or output caps, and a selection update containing them is rejected. Reasoning and tool metadata MUST match upstream capabilities.

#### Scenario: Refresh preserves operator intent
- **WHEN** a refresh changes prices and adds a model in selected mode
- **THEN** prices update, existing selections and display names remain, and the new model is disabled

#### Scenario: Removed model
- **WHEN** a successful refresh omits a selected model
- **THEN** the dashboard marks it unavailable and requests do not fall through to subscription accounts or another model

#### Scenario: All conversation models
- **WHEN** an operator enables all-model mode and the catalog adds an eligible conversation model
- **THEN** it is available without adding image models or losing saved selections

#### Scenario: Provider limits
- **WHEN** the catalog reports 1000000 context with a 500000 `top_provider` context
- **THEN** the model is advertised with a 500000 context window

#### Scenario: Stored caps after upgrade
- **WHEN** an account's stored selections contain context or output caps from before this change
- **THEN** the migration removes them and the next synchronization re-projects provider limits
