# Model Source Routing Specification

## Purpose

Define capability-based routing and accounting for OpenAI-compatible model sources, including field-preserving embeddings forwarding.

## Requirements

### Requirement: Model sources declare an embeddings capability

Each model source MUST carry a persisted `supports_embeddings` boolean
capability flag. The flag MUST default to disabled, so a source created or
migrated without an explicit value MUST NOT be treated as embeddings-capable.
The model-source create, read, and update contracts MUST expose the flag, and
the stored value MUST survive a round trip through those contracts.

#### Scenario: existing sources default to disabled

- **GIVEN** a model source row that predates the embeddings capability
- **WHEN** the schema migration runs
- **THEN** the source reports `supports_embeddings` as disabled
- **AND** its existing chat-completions, responses, and audio-transcription
  routing is unchanged

#### Scenario: capability round-trips through the API

- **WHEN** a client creates or updates a model source with the embeddings
  capability enabled
- **THEN** reading the source back reports the capability as enabled

#### Scenario: omitted capability parses as disabled

- **WHEN** a model-source payload omits `supports_embeddings`
- **THEN** it parses as disabled rather than failing validation

### Requirement: Embeddings route only to capable model sources

The system SHALL expose `POST /v1/embeddings` and MUST serve it only from an
enabled model source of kind `openai_compatible` that declares the embeddings
capability and has the requested model enabled. Embeddings requests MUST NOT
fall back to subscription-backed accounts. When the caller presents an API key
restricted to a set of sources, selection MUST stay inside that set. Beyond
the validated `model` and `input` fields, the request payload MUST be
forwarded to the source verbatim.

#### Scenario: capable source serves the request

- **GIVEN** an enabled model source declaring the embeddings capability with
  the requested model enabled
- **WHEN** a client posts to `/v1/embeddings`
- **THEN** the proxy forwards the payload to that source's `/embeddings`
  endpoint and returns the upstream JSON response

#### Scenario: no capable source is a model error

- **GIVEN** no enabled model source declares the embeddings capability for
  the requested model
- **WHEN** a client posts to `/v1/embeddings`
- **THEN** the proxy returns 404 with an OpenAI-format error envelope using
  code `model_not_found`
- **AND** the request is not routed to a subscription-backed account

#### Scenario: source-restricted API key cannot escape its set

- **GIVEN** an API key restricted to a set of model sources
- **WHEN** the only embeddings-capable source for the model is outside that
  set
- **THEN** the proxy returns `model_not_found`

### Requirement: Embeddings requests are accounted like other source routes

Embeddings responses MUST be inspected for prompt and total token usage. When
the caller's API key requires usage for settlement and the source response
reports none, the proxy MUST fail closed with `usage_unavailable` rather than
serving unmetered traffic. Every embeddings attempt that is dispatched to a
model source MUST produce a request-log entry, with `success` on a forwarded
response and `error` on a forwarding, usage, or settlement failure. That entry
MUST carry the upstream status code when a source returned an HTTP response,
and MUST record the upstream status as absent when the attempt failed before
any response was received. A request rejected before source selection succeeds
is not a dispatched attempt: it MUST NOT produce a request-log entry, because
no source was contacted and no reservation was consumed.

#### Scenario: missing usage fails closed for a limited key

- **GIVEN** an API key whose reservation requires reported usage
- **WHEN** the model source returns an embeddings response without a usage
  object
- **THEN** the proxy returns an error envelope using code `usage_unavailable`
- **AND** records an error request log

#### Scenario: forwarding error propagates the upstream status

- **WHEN** the model source returns an error status for an embeddings request
- **THEN** the proxy returns an OpenAI-format error envelope with that status
- **AND** records an error request log carrying the upstream status code

#### Scenario: transport failure records an attempt without an upstream status

- **WHEN** the request to the model source fails before any HTTP response is
  received
- **THEN** the proxy records an error request log for the attempt with no
  upstream status code

#### Scenario: unroutable model is not a logged attempt

- **GIVEN** no enabled model source declares the embeddings capability for
  the requested model
- **WHEN** a client posts to `/v1/embeddings`
- **THEN** the proxy returns the `model_not_found` envelope without writing a
  request-log entry
- **AND** no reservation is consumed for the rejected request

### Requirement: Embeddings source forwarding preserves field presence

For source-routed `POST /v1/embeddings` requests, the system MUST preserve both
the values and presence of fields beyond the validated `model` and `input`
fields. A field explicitly supplied as null MUST be forwarded as null, a field
omitted by the client MUST remain absent, and a non-null field MUST be forwarded
unchanged. This forwarding behavior MUST NOT change reservation settlement or
request-log metadata.

#### Scenario: explicit null extras remain present

- **WHEN** a client supplies `dimensions: null` and `user: null` in a
  source-routed embeddings request
- **THEN** the compatible source receives both keys with null values

#### Scenario: omitted extras remain absent

- **WHEN** a client omits `dimensions` and `user` from a source-routed
  embeddings request
- **THEN** the compatible source payload does not contain either key

#### Scenario: non-null extras and accounting remain unchanged

- **WHEN** a client supplies non-null embedding extras through a limited API
  key
- **THEN** the compatible source receives those values unchanged
- **AND** the reservation settles from reported usage
- **AND** the successful request log retains its model-source metadata and
  token counts

### Requirement: Owner-unavailable stream health preserves the recovery cause

The service SHALL use the original upstream error code for account-health
recovery when a Responses stream rewrites an upstream failure to
`previous_response_owner_unavailable`. The rewrite MUST NOT change
source-ownership selection, owner pinning, or stale-anchor matching.

#### Scenario: Owner-unavailable rewrite records original recovery code

- **WHEN** an upstream Responses failure with an account-recovery code is
  rewritten to `previous_response_owner_unavailable`
- **THEN** account health receives the original upstream code
- **AND** source ownership and stale-anchor classification remain unchanged

### Requirement: Source compaction history safety
Source compaction MUST reject unresolved previous-response or conversation handles with an actionable client error requesting materialized history. Source requests MUST reject unreadable native compaction checkpoints rather than replace history with a placeholder. Valid proxy-owned summaries MUST remain portable. Both the dedicated compact endpoint and terminal compaction triggers SHALL use the selected source for summarization.

#### Scenario: Unresolved compact continuation
- **WHEN** source compaction includes a previous-response handle whose history cannot be resolved
- **THEN** the proxy returns a client error without dispatching a summary request

#### Scenario: Retained compact continuation
- **WHEN** source compaction includes a resolvable previous-response handle
- **THEN** the proxy materializes the history before dispatching a stateless summarization request

### Requirement: Overflow compaction destination protocol
Subscription overflow with a terminal compaction trigger MUST use source synthetic compaction and preserve the overflow admission claims, attribution and settlement lifecycle.

#### Scenario: Compaction overflows to a source
- **WHEN** subscription overflow selects a source for a terminal compaction request
- **THEN** the source receives a non-streaming summarization turn and the client receives a proxy compaction envelope

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

### Requirement: Source Responses WebSocket transport
Responses clients SHALL use the same source models over HTTP and WebSocket. The proxy MUST bridge source SSE events into Responses WebSocket messages without requiring a client HTTP downgrade. Both transports MUST enforce the same model/source access and usage settlement. Disconnects MUST cancel and close owned upstream work. Switching to a subscription model MUST retain subscription routing.

#### Scenario: Source turn over WebSocket
- **WHEN** a client sends response.create for a source model
- **THEN** it receives Responses events on the same socket while upstream uses HTTP

#### Scenario: Source then subscription model
- **WHEN** an idle client socket switches from an OpenRouter model to a subscription model
- **THEN** the subscription model uses its normal account and transport selection

### Requirement: Stateless source continuation
For stateless sources the system SHALL reconstruct scoped previous-response history before dispatch and retain complete input and output under bounded private retention. It MUST preserve tool identities and MUST return an actionable previous_response_not_found error if required state is missing. Upstream MUST receive complete history without a previous_response_id or store:true.

#### Scenario: Tool continuation
- **WHEN** a client sends a previous response id with a tool output
- **THEN** the provider receives the preceding conversation and matching tool call exactly once

#### Scenario: Expired continuation
- **WHEN** required retained history has expired
- **THEN** the client receives previous_response_not_found requesting full history and no incomplete request is sent upstream
