## MODIFIED Requirements

### Requirement: Codex compaction triggers are bridged into compact output

When `POST /backend-api/codex/responses` receives a request whose top-level `input` array contains exactly one `{"type":"compaction_trigger"}` item as its final element and the request is served by a subscription account, the proxy SHALL dispatch it as an ordinary Responses turn through the same HTTP bridge or HTTP streaming path as any other turn. The forwarded body MUST retain the client's tool declarations, `tool_choice`, `parallel_tool_calls`, text options and complete input, with the single terminal trigger unchanged. The proxy MUST NOT rebuild the turn as a compact request, trim its input to the compact wire budget or elide images. The upstream SSE lifecycle, including its compaction output item, SHALL be relayed to the client as for any turn, and the turn SHALL establish the same session/turn-state ownership as any bridged turn. A successful turn whose output ends with exactly one native compaction item SHALL record native checkpoint provenance for that conversation exactly as a websocket compaction turn does. The proxy MUST reject duplicate or non-terminal top-level `compaction_trigger` placement locally with HTTP 400 `invalid_request_error` before any upstream work.

Explicit compact requests (`POST /backend-api/codex/responses/compact`) SHALL send the upstream compact request to `POST /backend-api/codex/responses` with `stream=true`, `store=false` and exactly one terminal `compaction_trigger`, accept the upstream SSE response, and reconstruct one normalized compact response item from the terminal response lifecycle; they MUST NOT require the legacy `/backend-api/codex/responses/compact` upstream route to be available.

For Codex-affinity standalone compact requests, `POST /backend-api/codex/responses/compact` SHALL remain available as a compatibility endpoint with its subscription-backed compact routing contract, and SHALL normalize an upstream remote-compaction-v2 response that includes historical message output plus a compaction summary into the single compact output item required by Codex clients. A valid upstream `cmp_` compaction item `id` and any non-empty `status` MUST be preserved in that normalized output item. An empty, non-string, or non-`cmp_` ID MUST be omitted rather than rewritten; encrypted content MUST remain unchanged.

OpenAI-style `/v1/responses/compact` is otherwise unchanged by this requirement; when it receives duplicate top-level `compaction_trigger` items, codex-lb preserves the existing compatibility behavior and the forwarded compact input contains one terminal trigger.

#### Scenario: terminal trigger emits a complete compact lifecycle

- **WHEN** a subscription-served `POST /backend-api/codex/responses` request ends with exactly one top-level `compaction_trigger`
- **THEN** the turn is forwarded as an ordinary turn and the upstream request carries the client's tools and `parallel_tool_calls`
- **AND** the proxy does not call compact handling
- **AND** the client receives the upstream SSE lifecycle, including its compaction output item, as relayed for any turn

#### Scenario: terminal trigger becomes one compact-wire trigger

- **WHEN** a subscription-served `POST /backend-api/codex/responses` request ends with exactly one top-level `compaction_trigger`
- **THEN** the upstream request carries the complete client input, including inline images, untrimmed
- **AND** it contains exactly one terminal `compaction_trigger` item, unchanged

#### Scenario: encrypted compaction item identity survives trigger streaming

- **WHEN** the upstream turn streams an encrypted compaction item with an upstream ID and status
- **THEN** the relayed item keeps that ID, status and encrypted content unchanged
- **AND** the proxy does not synthesize a replacement item ID

#### Scenario: forwarded compaction turn records checkpoint provenance

- **WHEN** a forwarded terminal-trigger turn completes with exactly one native compaction item as its final output
- **THEN** the proxy records native checkpoint provenance for that conversation and serving account

#### Scenario: malformed trigger placement is rejected

- **WHEN** a `POST /backend-api/codex/responses` or
  `POST /backend-api/codex/responses/compact` request contains duplicate or
  non-terminal top-level `compaction_trigger` items
- **THEN** the proxy returns HTTP 400 with `invalid_request_error`
- **AND** it does not attempt upstream work

#### Scenario: Codex compact transport uses the Responses stream

- **WHEN** a client calls `POST /backend-api/codex/responses/compact`
- **THEN** the proxy sends the compact request to
  `POST /backend-api/codex/responses` with `stream=true` and `store=false`
- **AND** it accepts the upstream SSE response and reconstructs one normalized
  compact response item from the terminal response lifecycle
- **AND** it does not require the legacy `/backend-api/codex/responses/compact`
  upstream route to be available

#### Scenario: Legacy message-shaped compact output does not get a rewritten item ID

- **WHEN** the upstream compact response exposes the encrypted compact payload
  as a legacy `message` item with a non-empty ID that does not begin with `cmp_`
- **THEN** the proxy converts that item to `type="compaction"` and omits the
  malformed ID
- **AND** the proxy preserves the encrypted content unchanged
- **AND** an existing ID that begins with `cmp_` is preserved byte-for-byte
- **AND** the proxy does not synthesize a `cmp_msg_...` ID
- **AND** ordinary message items outside the compact-output conversion remain
  unchanged

#### Scenario: Standalone Codex compact remains a compatibility endpoint

- **WHEN** a client calls `POST /backend-api/codex/responses/compact`
- **THEN** codex-lb preserves the endpoint and its subscription-backed compact
  routing contract
- **AND** malformed duplicate or non-terminal top-level triggers are rejected
  locally before any upstream compact attempt

#### Scenario: Codex-affinity standalone compact normalizes remote v2 output

- **WHEN** a Codex-affinity `POST /backend-api/codex/responses/compact` request receives upstream output that contains historical message items and one compaction summary item
- **THEN** the JSON response body contains exactly one `output` item for that compaction summary
- **AND** the normalized item preserves the compaction summary's valid `cmp_`-prefixed upstream ID and status
- **AND** it does not expose historical message items as standalone compact output

#### Scenario: OpenAI-compatible compact normalizes duplicate triggers

- **WHEN** a client calls `POST /v1/responses/compact` with duplicate
  top-level `compaction_trigger` items
- **THEN** codex-lb preserves the existing compatibility behavior and returns
  HTTP 200 when the compact operation succeeds
- **AND** the forwarded compact input contains one terminal trigger


### Requirement: Compact trimming preserves prioritised historical side effects

The service MUST retain recognised historical side-effect tool calls as bounded
priority context when an oversized compact input is trimmed. It MUST use the
same side-effect classifier as downstream replay
deduplication. This includes code-mode `exec` and `collaboration` wrapper calls
as well as their lower-level tool spellings and recognised parallel batches.

For each retained historical side effect, compact trimming MUST retain its
matching call and output together. The service MUST reserve space for that
complete pair before selecting optional ordinary head or tail context. Required
state anchors and the current required item remain mandatory; if they leave no
room for a historical pair, the service MAY drop that pair together and retain a
trim marker instead.

A recognised side-effect call without a non-empty `call_id` MUST NOT be
retained as a historical side-effect anchor, because it cannot form a verified
call/output pair.

#### Scenario: Code-mode side effect survives an oversized compact input

- **WHEN** an oversized compact input contains a historical custom `exec` or
  `collaboration` call with its matching output outside required state context
- **THEN** the trimmed upstream input retains both the call and its output when
  the pair fits with required state
- **AND** optional ordinary tail context is dropped before that pair

#### Scenario: Historical side-effect pair cannot fit with required state

- **WHEN** required state anchors and the current required item leave no room
  for a historical side-effect call and its matching output
- **THEN** compact trimming drops the entire historical pair
- **AND** it does not retain only one member of that pair

#### Scenario: Side-effect call lacks a usable pair key

- **WHEN** an oversized compact input contains a recognised historical
  side-effect call without a non-empty `call_id`
- **THEN** compact trimming does not preserve that call as a side-effect anchor
- **AND** it does not emit an unpaired historical side-effect call upstream

#### Scenario: Final compact wire expansion is rejected locally

- **WHEN** Unicode escaping, JSON array framing, or image inlining makes the final compact input exceed the upstream limit
- **THEN** the service returns `responses_compact_input_too_large` before an upstream attempt
- **AND** any API-key reservation is released
- **AND** no upstream account is penalized

#### Scenario: Terminal compaction trigger validates before admission

- **WHEN** a streaming Responses request ends with `compaction_trigger` on a subscription-served HTTP turn
- **THEN** compact trimming and the compact wire budget do not apply, because the turn is forwarded unchanged
- **AND** malformed trigger placement is still rejected before admission, reservation, account selection, or upstream work

#### Scenario: Enforced non-Lite model rejects Lite input

- **WHEN** API-key policy rewrites Lite-shaped input to a model whose catalog metadata disables Responses Lite
- **THEN** the service rejects the request before any upstream HTTP or websocket attempt

#### Scenario: Replayed code-mode side effects are emitted once

- **WHEN** reconnect replay repeats the same code-mode `exec` or `collaboration` call identity
- **THEN** the downstream client receives that side-effecting call only once

#### Scenario: Distinct code-mode calls remain distinct

- **WHEN** request history has different call IDs with identical code-mode source text and matching outputs
