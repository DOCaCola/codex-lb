# OpenRouter Accounts Specification

## Purpose

Provide native OpenRouter account management, selected model discovery and truthful usage visibility without an intermediate provider gateway.

## Requirements

### Requirement: Native OpenRouter accounts
Operators SHALL create, rename, enable, disable and delete OpenRouter accounts in the Accounts dashboard using an inference key and optional separate management key. Credentials MUST be encrypted at rest and absent from dashboard responses. Invalid inference keys MUST prevent account creation.

#### Scenario: Valid account creation
- **WHEN** an operator submits a valid inference key
- **THEN** the account is created with no models enabled and its credentials are not returned

### Requirement: Synchronized model selection
The system SHALL synchronize the authenticated model catalog on creation, periodically and on manual refresh. It MUST preserve explicit selections and overrides, keep new models disabled, mark removed models unavailable, and retain the last successful snapshot on synchronization failure. Only selected available models SHALL be advertised and routed. Context MUST default to at most 262144 tokens and MUST NOT exceed upstream limits. Reasoning and tool metadata MUST match upstream capabilities.

#### Scenario: Refresh preserves operator intent
- **WHEN** a refresh changes prices and adds a model
- **THEN** prices update, existing selections and context caps remain, and the new model is disabled

#### Scenario: Removed model
- **WHEN** a successful refresh omits a selected model
- **THEN** the dashboard marks it unavailable and requests do not fall through to subscription accounts or another model

### Requirement: Truthful OpenRouter monitoring
The dashboard SHALL separately display account credit balance, key allowance, provider usage, free-request quota and observation timestamps when known. Unavailable monitoring MUST be shown as unknown or stale, never zero or unlimited. Account credits MUST use the management credential when configured.

#### Scenario: No management credential
- **WHEN** an inference key is configured without a management key
- **THEN** key monitoring remains available and account credit balance is unavailable

### Requirement: Provider protocol and account selection
OpenRouter requests MUST preserve supported custom tools, namespaces, reasoning and terminal events, use the selected upstream model id, and report provider-supplied cost when available. Selection and retries MUST remain within client-key source restrictions, preserve the requested model, and MUST NOT retry after content delivery. A model-specific failure MUST NOT disable unrelated models.

#### Scenario: Limited account fails before delivery
- **WHEN** a selected account returns a retryable error before content delivery and another permitted account serves that model
- **THEN** the request may proceed through that eligible account without changing the model or duplicating settlement
