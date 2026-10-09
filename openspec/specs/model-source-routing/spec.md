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
Source compaction MUST reject unresolved previous-response or conversation handles
with an actionable client error requesting materialized history. Source requests
MUST reject unreadable native compaction checkpoints rather than replace history
with a placeholder. Valid proxy-owned summaries MUST remain portable. Both the
dedicated compact endpoint and terminal compaction triggers SHALL use the selected
source for summarization. Source history MUST be materialized before dispatch
without native compact size reduction. Portable text, tool results and images
MUST NOT be omitted or shortened to meet the native compact wire budget. Source
summarization SHALL disable automatic input truncation. Unsupported state,
provider capacity refusals and incomplete output MUST return errors without a
successful compaction checkpoint or replacement of retained original history.
Native OpenAI compact wire behavior SHALL remain unchanged.
Source model request overrides MUST NOT replace compaction history/instructions,
enable tools or automatic truncation, or attach persisted continuation handles.
Claude summarization SHALL carry the client's tools, tool_choice and
parallel_tool_calls unchanged so its prompt prefix matches ordinary turns; other
sources SHALL summarize without tool declarations. The summarization instruction
SHALL forbid tool calls, and tool, custom-tool or hosted-search output MUST fail
compaction without a checkpoint or replacement of retained original history.
Claude compaction MUST authenticate signed history and SHALL prefer its original
account and model, replaying signed blocks verbatim there. Completed signed
thinking that cannot keep its signature on the selected account or model, or
whose historical signature the upstream rejects, SHALL reach the summarizer as
readable historical assistant text in original order without fabricated
signatures; completed redacted thinking, which has no readable content, SHALL
produce no wire block. Signed state in the active turn of the client-supplied
history and hosted search state MUST remain bound to their original account and
model or fail explicitly.

#### Scenario: Unresolved compact continuation
- **WHEN** source compaction includes a previous-response handle whose history cannot be resolved
- **THEN** the proxy returns a client error without dispatching a summary request

#### Scenario: Retained compact continuation
- **WHEN** source compaction includes a resolvable previous-response handle
- **THEN** the proxy materializes the history before dispatching a stateless summarization request

#### Scenario: History exceeds the native compact budget
- **WHEN** source compaction contains readable history above 100k estimated tokens
- **THEN** the summarizer receives the complete history in original order with images and tool-result contents preserved

#### Scenario: Source capacity refusal
- **WHEN** the source rejects a compact request because complete history exceeds its capacity
- **THEN** the error is returned without retrying shortened history, emitting a successful checkpoint or replacing retained original history

#### Scenario: Native compaction compatibility
- **WHEN** native OpenAI compact serialization is used
- **THEN** its existing normalization and wire-budget behavior remain active

#### Scenario: Claude compaction reuses the conversation prefix
- **WHEN** Claude compacts a conversation whose requests declare tools, over the compact endpoint or a terminal compaction trigger
- **THEN** the summarizer receives the same tools, tool choice and system as an ordinary turn, with the turn's messages as an unchanged prefix followed by the summarization instruction

#### Scenario: Summarizer calls a tool
- **WHEN** the source returns a tool, custom-tool or hosted-search call during compaction
- **THEN** the proxy returns model_source_compaction_invalid without a checkpoint and retained original history remains usable

#### Scenario: Tool-free source summarization
- **WHEN** OpenRouter or another non-Claude source compacts a conversation that declares tools
- **THEN** the summarization request contains no tool declarations

#### Scenario: Signed Claude history on another route
- **WHEN** compaction runs on another account or model than completed signed thinking, its owner is unavailable, completed owners differ or the upstream rejects a historical signature
- **THEN** the summarizer receives that thinking as readable assistant text with all other history unchanged, without signatures from another route

#### Scenario: Signed Claude history cannot be preserved
- **WHEN** compaction contains active-turn signed state or hosted search state whose owner or model is unavailable or conflicting
- **THEN** it returns an error without dispatching or dropping that state

#### Scenario: Conflicting model overrides
- **WHEN** source request overrides replace input or enable tools, persisted continuation or automatic truncation
- **THEN** the protected compaction contract remains active while compatible generation overrides can still apply

### Requirement: Overflow compaction destination protocol
Subscription overflow with a terminal compaction trigger MUST use source synthetic compaction and preserve the overflow admission claims, attribution and settlement lifecycle.

#### Scenario: Compaction overflows to a source
- **WHEN** subscription overflow selects a source for a terminal compaction request
- **THEN** the source receives a non-streaming summarization turn and the client receives a proxy compaction envelope

### Requirement: Source local compaction marker projection

Source Responses inference and summarization SHALL distinguish payload-free local context_compaction markers from data-bearing checkpoints. A marker with missing or null encrypted_content and only recognized type, id and internal_chat_message_metadata_passthrough metadata SHALL produce no source wire item. Surrounding summaries, messages, tools and images SHALL remain ordered and unchanged, and retained logical input SHALL keep the original marker. Native OpenAI replay SHALL remain unchanged. The policy SHALL apply to public HTTP/WebSocket and expanded continuation.

Opaque native checkpoints without verified readable recovery, corrupt proxy summaries, malformed ciphertext and unsupported marker payload fields MUST fail before upstream dispatch with compaction_history_unavailable and an indexed input parameter. Failed projection MUST NOT partially replace input or fabricate summary text. Rejection diagnostics SHALL contain only request ID, input index, known compaction subtype, ciphertext presence and a bounded reason. Successful marker omission SHALL log one aggregate count, never content or raw identifiers.

#### Scenario: Local compaction then model switch
- **WHEN** a client replays a payload-free context_compaction marker and an ordinary summary to Claude
- **THEN** Claude receives the complete readable context without the marker and retained history keeps both original items

#### Scenario: Native opaque checkpoint
- **WHEN** a source request contains encrypted native compaction state without verified readable recovery
- **THEN** it fails at its original input index with content-free subtype diagnostics rather than replacing history with a note

#### Scenario: Malformed marker
- **WHEN** context_compaction carries empty or wrong-typed ciphertext or an unsupported payload field
- **THEN** preparation fails without discarding that item or sending incomplete context

#### Scenario: Native marker replay
- **WHEN** a native OpenAI request carries the same local marker
- **THEN** its native wire representation remains unchanged

#### Scenario: Continued replay and compact
- **WHEN** a retained source conversation containing a local marker is resumed or summarized
- **THEN** visible history remains available, markers do not reach the source, and no opaque checkpoint is silently omitted

### Requirement: Verified readable native checkpoint recovery

After successful settled native compaction, the proxy SHALL retain
digest-bound original model/account provenance without copying the conversation
or native ciphertext. Checkpoint recovery state SHALL be scoped to the
authenticated API key and addressed by the checkpoint digest; it MUST NOT depend
on the client conversation ID, so forked conversations replaying the same
checkpoint share it. Previously retained complete readable snapshots SHALL remain
usable while valid. Native requests and compaction results MUST remain unchanged.
Source preparation SHALL first use valid readable recovery before requesting a
handoff. Missing or cross-key provenance MUST NOT cause guessed-owner dispatch.

Existing readable snapshot restoration SHALL preserve complete ordered semantic
input. An exact recorded compact replacement prefix SHALL be removed only when it
directly precedes its checkpoint. Repeated user turns MUST NOT be deduplicated by
content alone. Recovery diagnostics MUST contain only request identity and
aggregate counts or bounded reasons.

#### Scenario: Normal native compaction
- **WHEN** native compaction succeeds, including with older opaque history
- **THEN** only checkpoint provenance is captured and no summary request is made

#### Scenario: Available readable recovery
- **WHEN** source preparation finds a valid readable checkpoint snapshot for the same key
- **THEN** it restores that input without additional native generation

#### Scenario: Forked conversation
- **WHEN** a conversation with a new conversation ID replays a checkpoint whose recovery state was recorded for the same key under another conversation
- **THEN** source preparation uses that snapshot, provenance or handoff summary exactly as for the original conversation

#### Scenario: Another API key
- **WHEN** a different API key replays the same checkpoint ciphertext
- **THEN** none of the original key's recovery state is used

#### Scenario: Unknown legacy checkpoint
- **WHEN** a checkpoint has neither readable recovery, a valid handoff summary nor verified provenance
- **THEN** preparation fails at its original input index without dropping history

#### Scenario: Exact compact replacement prefix
- **WHEN** a source replays the exact preserved-message prefix returned with a retained checkpoint
- **THEN** recovery includes those messages once and leaves unrelated repeated turns intact

#### Scenario: Native and failed compact behavior
- **WHEN** native compaction succeeds or fails
- **THEN** its existing wire result and settlement are unchanged and failed compaction does not seed recovery

### Requirement: On-demand native checkpoint handoff

Only source requests containing an unreadable native checkpoint SHALL trigger
handoff. The proxy MUST authenticate scope and use the checkpoint's verified
original model/account under current access restrictions. The native request
SHALL contain that checkpoint and a handoff instruction, no tools, truncation,
continuation handles or unrelated conversation data. Account reselection MUST NOT
move handoff to another account. Native handoff SHALL transfer its independent
usage settlement and request log to the existing tracked persistence lifecycle
before destination dispatch. Cancellation MUST close owned upstream work and
preserve ownership of pending persistence cleanup.

Completed, nonempty, nonrefused summary text SHALL replace only the checkpoint;
surrounding messages/tools/images SHALL remain ordered and unchanged. Invalid,
incomplete or refused output and native owner/model errors MUST stop preparation
without destination dispatch. Portable summaries and normal native requests MUST
NOT generate handoffs.

Handoff summaries and provenance SHALL use bounded private 30-day retention,
without storing the whole conversation. Successful handoffs SHALL be reused across
turns, forked conversations and process restarts for the same authenticated API
key. Valid cached summaries SHALL remain usable after provenance expiry, subject
to current access restrictions. Concurrent generation for the same key and
checkpoint MUST NOT duplicate native requests. Expired, evicted or corrupt state
MUST NOT produce partial context. Diagnostics MUST NOT include ciphertext, summary
text or conversation content.

#### Scenario: HTTP and WebSocket switch
- **WHEN** an authenticated source request replays a checkpoint with verified native provenance
- **THEN** its original account generates one metered handoff and the destination receives readable summary plus unchanged visible history

#### Scenario: Repeated source turn
- **WHEN** another source request replays a previously handed-off checkpoint
- **THEN** the cached summary is reused without another native request

#### Scenario: Forked source turn
- **WHEN** a forked conversation of the same key replays a previously handed-off checkpoint
- **THEN** the cached summary is reused without another native request

#### Scenario: Concurrent switch
- **WHEN** another worker is generating the same handoff for the same key and checkpoint
- **THEN** the request returns an explicit retryable busy error without duplicate generation

#### Scenario: Owner unavailable or restricted
- **WHEN** generation is required and the original account/model is unavailable or excluded by current API-key policy
- **THEN** handoff fails without account failover or destination dispatch

#### Scenario: Invalid handoff output
- **WHEN** the native response is incomplete, refused, malformed or empty
- **THEN** it is not cached as portable context and the destination is not contacted

#### Scenario: Ordinary source request
- **WHEN** the source input is readable or contains a valid proxy summary
- **THEN** no handoff work or extra native usage occurs

#### Scenario: Provenance expired after successful handoff
- **WHEN** a valid handoff summary for the same key outlives its original provenance
- **THEN** it is reused only after checking its recorded model/account against current key permissions

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

### Requirement: Source WebSocket retry metadata
Source HTTP errors converted to WebSocket error events SHALL preserve validated Retry-After in a headers object alongside status and error. Credential and unrelated headers MUST NOT be forwarded. The bridge MUST NOT invent successful events or alter status to force client retries.

#### Scenario: Rate-limited source
- **WHEN** a source response returns429 with a valid Retry-After
- **THEN** the WebSocket error retains the status, error and retry header

### Requirement: Settled source Responses stream failures
Source Responses forwarding failures after stream start SHALL settle and release the failed attempt exactly once before delivering one structured error event over HTTP or WebSocket. The event SHALL preserve status and error with only validated Retry-After metadata. The WebSocket SHALL remain usable for later turns. No completion, generation retry or retained successful response SHALL be fabricated. Cancellation MUST remain cancellation.

#### Scenario: Projection failure after output
- **WHEN** a source adapter raises a forwarding failure after delivering assistant text
- **THEN** the client receives a structured error, the request log preserves the failure cause, and no successful response is retained

#### Scenario: Next WebSocket turn
- **WHEN** a source stream fails and the client submits another valid request on the same WebSocket
- **THEN** the next turn can complete without reopening the connection

#### Scenario: Retry metadata
- **WHEN** a stream failure carries a valid Retry-After and unrelated upstream headers
- **THEN** the error event preserves only the validated retry hint, status and error

#### Scenario: Disconnect during output
- **WHEN** the downstream client disconnects before an error or completion
- **THEN** normal cancellation and cleanup apply without sending a synthetic failure or completion

### Requirement: Source tool calls declare plaintext arguments
Responses output forwarded from any model source SHALL mark each `function_call` whose tool declaration in the client request marks a parameter `encrypted` with `encrypted_function_args: []`, on non-stream payloads and on every streamed event carrying the item. Declarations SHALL be matched by the client's namespace and name, independent of provider wire aliases.

#### Scenario: OpenRouter subagent spawn
- **WHEN** an OpenRouter model calls the namespaced collaboration `spawn_agent` tool through an aliased wire name
- **THEN** the client receives the restored namespace and name with `encrypted_function_args: []`

#### Scenario: Generic source
- **WHEN** a non-OpenRouter source returns a call to a tool with an encrypted parameter
- **THEN** the forwarded call carries `encrypted_function_args: []`

### Requirement: Inter-agent messages are source user messages
Model-source Responses forwarding SHALL send plaintext `agent_message` items as user messages carrying the item's content unchanged. Codex's agent-message header naming the recipient and sender is part of that content; the proxy MUST NOT add another. An `agent_message` with an `encrypted_content` part SHALL fail with `nonportable_agent_message`.

#### Scenario: Child reports to a source-served parent
- **WHEN** a request to a model source contains a plaintext `agent_message`
- **THEN** the source receives a user message with that content, including Codex's header, exactly once

### Requirement: Provider-attributed source errors
Gateway-generated error messages for a model-source request SHALL name the provider that serves it: "Claude" for Claude accounts, "OpenRouter" for OpenRouter accounts and "OpenAI-compatible model source" for generic sources. Error codes, statuses and upstream-provided messages SHALL remain unchanged.

#### Scenario: Claude connection failure
- **WHEN** a Claude account's request fails to resolve its upstream host
- **THEN** the message reads "Claude request failed: ClientConnectorDNSError" with code `model_source_unreachable`

#### Scenario: Generic source timeout
- **WHEN** a generic OpenAI-compatible source misses its header deadline
- **THEN** the message names the OpenAI-compatible model source

### Requirement: Routed requests name the destination model in the Codex identity
Before dispatching a Responses request to a model source, the proxy SHALL rewrite a Codex identity sentence in `instructions` to name the destination source model's display name. This SHALL apply to the neutral catalog prompt and to a native GPT prompt replayed into a routed subagent. Instructions without a Codex identity sentence MUST be forwarded unchanged, and operator request overrides keep precedence.

#### Scenario: Replayed native prompt
- **GIVEN** a routed request whose instructions begin "You are Codex, an agent based on GPT-6."
- **WHEN** the request is dispatched to source model "Claude Opus 5.5"
- **THEN** the source receives "You are Codex, an agent running on Claude Opus 5.5." in place of that sentence

#### Scenario: Unrelated instructions
- **WHEN** a routed request carries instructions without a Codex identity sentence
- **THEN** the source receives them unchanged

### Requirement: Source failure terminals record the source's error
When a source stream ends with a `response.failed` or `error` terminal, the request-log row SHALL record the error code and message the source supplied in that terminal. The generic code `model_source_response_failed` SHALL apply only when the terminal carries no code. The attempt SHALL remain an error that releases its reservation, including when the client disconnects after receiving the failure.

#### Scenario: Source supplies a failure code
- **WHEN** a source ends a stream with `response.failed` carrying code `server_error` and a message
- **THEN** the request-log row records status error with code `server_error` and that message, and the reservation is released

#### Scenario: Typeless error record
- **WHEN** a source ends a stream with a typeless `{"error": {...}}` record carrying code `overloaded`
- **THEN** the request-log row records code `overloaded`

#### Scenario: Translated Claude refusal
- **WHEN** a translated Claude response fails because Claude refused
- **THEN** the request-log row records code `invalid_prompt`

#### Scenario: Failure without a code
- **WHEN** a source failure terminal carries no error code
- **THEN** the request-log row records `model_source_response_failed`

### Requirement: OpenAI-compatible providers are managed as accounts
User-defined `openai_compatible` model sources SHALL be created, listed,
selected, renamed, coloured, paused, resumed, edited and deleted on the Accounts
page alongside Codex, Claude and OpenRouter accounts, and SHALL NOT be managed
from Settings. Their detail SHALL show usage trends from
`GET /api/model-sources/{id}/trends`, the models with their pricing and the
connection details. `openai_compatible` SHALL be a provider identity for account
colours, provider marks and request-log attribution. Mutation controls SHALL be
unavailable to read-only sessions.

#### Scenario: Add an endpoint
- **WHEN** an operator chooses "API endpoint" in the add-account chooser
- **THEN** the OpenAI-compatible provider dialog opens and the created source appears in the Accounts list

#### Scenario: Settings no longer lists sources
- **WHEN** an operator opens Settings → Models
- **THEN** only the model catalogue is shown and no model-source request is issued

### Requirement: Provider-backed sources refuse model-source management
The model-source API SHALL refuse to update or delete a source whose kind is not
`openai_compatible` with a 400 that names the Accounts dashboard as the place to
manage it, leaving the source and its provider account unchanged.

#### Scenario: Deleting a Claude-backed source
- **WHEN** a client calls `DELETE /api/model-sources/{id}` for a Claude-backed source
- **THEN** the response is 400 and the Claude account and its source remain
