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

### Requirement: Unified account presentation
OpenRouter accounts SHALL appear in the existing dashboard account card/list collection and Accounts master/detail list, without a separate provider section. The UI SHALL use consistent surfaces, typography, status badges and privacy behavior. Provider-specific monitoring MUST retain its units, unknown/stale states and timestamps; dollar balances MUST NOT be counted as Codex subscription quotas.

#### Scenario: Mixed providers
- **WHEN** both Codex and OpenRouter accounts exist
- **THEN** both appear in the same dashboard collection in either view mode and in the same searchable Accounts list

#### Scenario: Provider selection
- **WHEN** an operator selects an OpenRouter account from the list or its dashboard details action
- **THEN** the shared detail column displays that account's monitoring, model selection and credential controls

#### Scenario: Add account
- **WHEN** an operator opens the existing add-account chooser
- **THEN** OpenRouter is available alongside the native account options

#### Scenario: Read-only and unavailable monitoring
- **WHEN** a read-only user views an OpenRouter account with unavailable or stale monitoring
- **THEN** those states remain explicit, account names follow privacy settings, and mutation controls are unavailable

#### Scenario: OpenRouter-only installation
- **WHEN** no native accounts exist but an OpenRouter account exists
- **THEN** both account pages display the provider account instead of a misleading empty state

#### Scenario: Consistent account actions
- **WHEN** an operator views an OpenRouter account's details
- **THEN** the UI offers Pause for an enabled account and Resume for a paused account using the same controls as native accounts, without a separate enabled switch
- **AND** shared actions use consistent sizing and destructive-delete styling, and mutation controls are disabled while busy or read-only

### Requirement: OpenRouter parameter capabilities govern projection
The system MUST retain synchronized supported parameters and advertise parallel-tool support only when tools and the parallel-tool parameter are supported. Unsupported `parallel_tool_calls: true` MUST be omitted; explicit unsupported `false` MUST return a clear unsupported-parameter error. Strict parameter routing and exact model identity MUST be preserved. Reasoning choices MUST be sorted in ascending effort without changing the supported set or default.

#### Scenario: Tool-only endpoint
- **WHEN** a model supports tools but not the parallel-tool parameter
- **THEN** permissive parallel hints are omitted and explicit serial constraints are rejected before dispatch

#### Scenario: Reversed provider efforts
- **WHEN** the provider lists xhigh, medium, low
- **THEN** clients receive low, medium, xhigh with the original default

### Requirement: OpenRouter errors conform to client error contracts
OpenRouter HTTP rejections MUST preserve their HTTP status and message while exposing string error codes and types to clients. WebSocket clients MUST receive a parseable terminal error rather than wait for a completion that will never arrive.

#### Scenario: Numeric provider error code
- **WHEN** OpenRouter rejects a WebSocket-backed turn with HTTP 404 and numeric code 404
- **THEN** the client receives an error frame with status 404 and a string code and the original message

### Requirement: Model capability filters
The model selector SHALL offer text generation, image generation, vision, tools, and reasoning filters based on catalog metadata. Multiple filters MUST match all selected capabilities and combine with name/ID search. Filtering MUST NOT change selected models, including unavailable selections. Operators MUST be able to clear capability filters and see explicit empty-result feedback.

#### Scenario: Filter image models with reference input
- **WHEN** an operator selects image generation and vision filters
- **THEN** only models with image generation metadata and image input support are shown, without removing hidden selections

### Requirement: Image catalog selection
The system SHALL synchronize OpenRouter's dedicated image catalog and selected image models' endpoint capabilities and pricing. Image selections MUST remain explicit and persist through refresh. Image-only models MUST be discoverable through `/v1/models` but MUST NOT be advertised as Codex conversation models or dispatched as chat/Responses models. The account model selector MUST distinguish images from text and display image billable units instead of fictitious text context or token caps.

#### Scenario: Selected image model
- **WHEN** an operator selects an available image model
- **THEN** public model discovery includes it, while the Codex conversation catalog excludes it

### Requirement: Public image routing
Public `/v1/images/generations` and multipart `/v1/images/edits` SHALL route explicitly selected `openrouter/` image models to OpenRouter's `/images` endpoint. The adapter MUST preserve the selected model, translate reference uploads to data URLs, validate endpoint capabilities, and reject unsupported parameters including masks without silent dropping. Native Codex image endpoints and bare OpenAI image model behavior MUST remain unchanged.

#### Scenario: Reference image editing
- **WHEN** a client edits using an enabled OpenRouter image model and uploaded reference images
- **THEN** the adapter forwards those references as `input_references` and returns base64 image results

### Requirement: Image lifecycle and accounting
Image dispatch MUST enforce model/source restrictions, pause state, cooldowns and request limits; it MUST NOT fall through to subscription accounts or retry non-idempotent image generation. Responses MUST use bounded memory, preserve upstream errors and Retry-After, terminate incomplete streams with an error, release connections on cancellation, and settle reservations exactly once. Completed usage MUST retain OpenRouter's reported dollar cost and token counts. Unknown cost MUST NOT be fabricated as zero. Partial images alone MUST NOT be billed as completed work.

#### Scenario: Streaming completion
- **WHEN** OpenRouter sends partial images followed by completion
- **THEN** the client receives Images SSE events and final usage is recorded once

#### Scenario: Native Codex generation
- **WHEN** a Codex-native client requests gpt-image-2
- **THEN** the existing native ChatGPT path is used without an OpenRouter override
