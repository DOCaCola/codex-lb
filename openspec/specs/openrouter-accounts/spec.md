# OpenRouter Accounts Specification

## Purpose

Provide native OpenRouter account management, selected model discovery and truthful usage visibility without an intermediate provider gateway.

## Requirements

### Requirement: Grouped account enrollment
The add-account chooser SHALL group actions under Codex, Claude, OpenRouter and
OpenAI-compatible in that order. Codex SHALL offer OAuth and file import; the
OpenAI-compatible group SHALL offer an API endpoint. Optional provider groups
SHALL be absent when unavailable. All options SHALL share icon sizing, alignment
and focus styling, and preserve close-before-open action handoff.

#### Scenario: All providers available
- **WHEN** an operator opens the account chooser with all providers available
- **THEN** Codex options appear first, followed by Claude, OpenRouter and OpenAI-compatible groups

#### Scenario: Optional provider unavailable
- **WHEN** a provider has no enrollment callback
- **THEN** its group is not rendered

### Requirement: Native OpenRouter accounts
Operators SHALL create, rename, enable, disable and delete OpenRouter accounts in the Accounts dashboard using an inference key and optional separate management key. Credentials MUST be encrypted at rest and absent from dashboard responses. Invalid inference keys MUST prevent account creation.

#### Scenario: Valid account creation
- **WHEN** an operator submits a valid inference key
- **THEN** the account is created with no models enabled and its credentials are not returned

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

### Requirement: OpenRouter manual routing policy
OpenRouter accounts SHALL persist normal, burn_first or preserve policy, defaulting to normal. Selection MUST apply cooldowns, model availability, exclusions and client-key restrictions before preferring burn_first over normal over preserve. Rotation SHALL occur within the highest-priority usable pool, without falling through to subscription accounts when sources are cooling down.

#### Scenario: Cooled priority account
- **WHEN** a burn-first account is cooling down and a normal account is eligible
- **THEN** the normal account is selected

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
OpenRouter HTTP rejections MUST preserve their HTTP status and sanitized message while exposing string error codes and types to clients when provided. Responses forwarding MUST retain its upstream 401 protection: return a generic proxy-credential 502 without reading the rejected credential body. WebSocket clients MUST receive a parseable terminal error rather than wait for a completion that will never arrive.

#### Scenario: Numeric provider error code
- **WHEN** OpenRouter rejects a WebSocket-backed turn with HTTP 404 and numeric code 404
- **THEN** the client receives an error frame with status 404 and a string code and the original message

### Requirement: Model capability filters
The model selector SHALL offer text generation, image generation, vision, tools, and reasoning filters based on catalog metadata. Multiple filters MUST match all selected capabilities and combine with name/ID search. Filtering MUST NOT change selected models, including unavailable selections. Operators MUST be able to clear capability filters and see explicit empty-result feedback.

#### Scenario: Filter image models with reference input
- **WHEN** an operator selects image generation and vision filters
- **THEN** only models with image generation metadata and image input support are shown, without removing hidden selections

### Requirement: Safe OpenRouter provider diagnostics
OpenRouter HTTP 403 rejections MUST retain their status without being labeled invalid proxy credentials solely from that status. Structured nested provider reasons and provider names SHALL appear in the sanitized message visible to clients and request logs. The system MUST bound error body reads and diagnostic lengths, redact configured and recognizable credential values before truncation, and exclude arbitrary raw metadata. Existing unknown-source credential protection and OpenRouter 401 protection MUST remain unchanged.

#### Scenario: Provider rejects a request
- **WHEN** OpenRouter returns 400 with a generic message and structured provider metadata
- **THEN** clients and request logs include the sanitized provider reason without raw metadata or credential values

#### Scenario: Funding or policy denial
- **WHEN** OpenRouter returns 403 with a denial message
- **THEN** the client sees status 403 and a sanitized reason, not an assertion that credentials are invalid

#### Scenario: Unusable error body
- **WHEN** an OpenRouter error body is oversized or not valid JSON
- **THEN** the original error status is retained with a generic message and no raw body disclosure

### Requirement: Bounded reversible OpenRouter tool identities
OpenRouter tool names SHALL meet the 64-character ASCII function-name constraint
without changing client-visible names or namespace identities. Declarations,
historical calls and tool choices MUST use consistent deterministic identities.
Streaming and non-streaming Chat and Responses outputs MUST restore original
identities before delivery or replay persistence. Arguments, call IDs and tool
outputs MUST remain unchanged. Native OpenAI and other providers MUST be unaffected.

#### Scenario: Long document tool
- **WHEN** a namespaced MCP document tool exceeds the upstream name limit
- **THEN** its upstream alias fits the limit and the returned call has the original name and namespace

#### Scenario: Replay and selection
- **WHEN** a request selects a tool or replays a historical-only tool call
- **THEN** the same identity receives the same alias regardless of declaration order

#### Scenario: Distinct identities
- **WHEN** tool identities share a flattened spelling or resemble an alias
- **THEN** they remain distinct and restore to their respective original identities

#### Scenario: Streamed tool calls
- **WHEN** an aliased call arrives over arbitrarily chunked SSE
- **THEN** client-visible call events and terminal output restore the original identity

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

### Requirement: OpenRouter account tier display
Dashboard cards, account lists and account details SHALL derive Free or Paid from
the key metadata's is_free_tier flag. Missing metadata SHALL show Unknown, and
retained metadata after refresh failure SHALL be marked stale. Paid MUST NOT
imply a specific Standard, Business or Enterprise subscription.

#### Scenario: Non-free key
- **WHEN** OpenRouter reports is_free_tier false
- **THEN** the account displays Paid without inferring a commercial plan

### Requirement: Friendly upstream transport labels
The dashboard SHALL display openai_compatible_http as HTTP while preserving the
underlying transport value in storage and APIs.

#### Scenario: OpenRouter upstream HTTP
- **WHEN** a request uses openai_compatible_http upstream
- **THEN** its upstream transport badge reads Up HTTP

### Requirement: Gateway-observed OpenRouter timing
OpenRouter Chat and Responses forwarding SHALL record per-attempt duration using
a monotonic clock. Streaming TTFT SHALL measure from upstream attempt start to
first nonempty generated text, reasoning or tool arguments. Metadata, keepalives,
role-only chunks and terminal/error snapshots MUST NOT fabricate TTFT. HTTP and
WebSocket clients SHALL use the same measurement path. Nonstreaming TTFT and
unobserved first output MUST remain unknown.

#### Scenario: Bookkeeping before output
- **WHEN** a stream sends creation and keepalive events before a text delta
- **THEN** TTFT records the text delta's arrival, not the earlier events

#### Scenario: No generated delta
- **WHEN** a response only contains a terminal snapshot or nonstreaming JSON
- **THEN** duration is available but TTFT and estimated generation TPS are unknown

### Requirement: Truthful OpenRouter throughput
OpenRouter generation TPS SHALL use reported total output tokens over observed
duration after first output, including reasoning tokens. Dashboard TPS SHALL be
labeled estimated. Dashboard and reports MUST exclude unsuccessful requests,
unknown timing or output usage, and generation windows shorter than one second.
Other providers' existing metrics MUST remain unchanged.

#### Scenario: Successful measurable stream
- **WHEN** a successful stream reports 100 output tokens and a two-second generation window
- **THEN** its estimated throughput is 50 tokens per second

#### Scenario: Buffered or failed turn
- **WHEN** generation spans less than one second or the request fails
- **THEN** it contributes no OpenRouter generation TPS value

### Requirement: OpenRouter assistant messages carry a Responses phase

OpenRouter Responses output SHALL deliver each assistant message with a Responses `phase`. A phase sent by OpenRouter
MUST be kept unchanged. A message without one SHALL receive `commentary` when another output item follows it. The last
such message of a completed response SHALL receive `final_answer`, or `commentary` when the response contains a
`function_call` or `custom_tool_call`. The last such message of an incomplete or failed response SHALL remain without a
phase. A streamed message's `response.output_item.done` SHALL be delivered once its phase is known, and the terminal
response output SHALL carry the same phases. When a stream ends or fails without a terminal event, a held message
SHALL be delivered without a phase before the stream ends.

#### Scenario: answer after commentary

- **WHEN** an OpenRouter model streams a message, a reasoning item and a second message, and the response completes
- **THEN** the first message is done with phase `commentary` before the reasoning item is added
- **AND** the second message is done with phase `final_answer`
- **AND** `response.completed` output and the replayed history carry the same phases

#### Scenario: message in a tool-requesting response

- **WHEN** a completed OpenRouter response ends with a message after a function call
- **THEN** that message has phase `commentary`

#### Scenario: truncated response

- **WHEN** an OpenRouter response is incomplete or failed after a message
- **THEN** its last message is done without a phase

#### Scenario: native phase

- **WHEN** OpenRouter sends an assistant message with a phase
- **THEN** the client receives the event unchanged
