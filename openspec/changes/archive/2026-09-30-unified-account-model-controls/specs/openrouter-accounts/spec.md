## MODIFIED Requirements

### Requirement: Synchronized model selection
The system SHALL synchronize the authenticated model catalog on creation, periodically and on manual refresh. It MUST preserve explicit selections and overrides, mark removed models unavailable, and retain the last successful snapshot on synchronization failure. Selected mode SHALL keep new models disabled and advertise/route only selected available models. Explicit all-model mode SHALL advertise/route all eligible conversation models while retaining curated choices and keeping image selections explicit. Context MUST default to at most 262144 tokens and MUST NOT exceed upstream limits. Reasoning and tool metadata MUST match upstream capabilities.

#### Scenario: Refresh preserves operator intent
- **WHEN** a refresh changes prices and adds a model in selected mode
- **THEN** prices update, existing selections and context caps remain, and the new model is disabled

#### Scenario: Removed model
- **WHEN** a successful refresh omits a selected model
- **THEN** the dashboard marks it unavailable and requests do not fall through to subscription accounts or another model

#### Scenario: All conversation models
- **WHEN** an operator enables all-model mode and the catalog adds an eligible conversation model
- **THEN** it is available without adding image models or losing saved selections

## ADDED Requirements

### Requirement: OpenRouter manual routing policy
OpenRouter accounts SHALL persist normal, burn_first or preserve policy, defaulting to normal. Selection MUST apply cooldowns, model availability, exclusions and client-key restrictions before preferring burn_first over normal over preserve. Rotation SHALL occur within the highest-priority usable pool, without falling through to subscription accounts when sources are cooling down.

#### Scenario: Cooled priority account
- **WHEN** a burn-first account is cooling down and a normal account is eligible
- **THEN** the normal account is selected
