## ADDED Requirements

### Requirement: Codex compaction is destination-aware

When a valid terminal `compaction_trigger` targets a subscription-backed model,
the proxy SHALL preserve the existing native compact flow and synthetic SSE
lifecycle. Immediately before serializing any native subscription-backed
Responses request, the proxy MUST replace every non-empty plaintext `content`
array on a top-level `reasoning` input item with an empty array and MUST remove
that item's output-only `status` field. This requirement MUST cover direct HTTP,
direct WebSocket, HTTP-session bridge, and prepared replay request bodies.
Source-routed Responses requests MUST NOT receive this native-boundary
sanitation.

Immediately before any native or source-routed Responses request with
`store: false` is sent, the proxy MUST remove `id` from every top-level input
item unless that item carries non-empty opaque `encrypted_content`. It MUST
preserve opaque-state IDs, `call_id`, and all other item fields. Requests whose
effective `store` value is true or omitted MUST retain their item IDs.

When the terminal trigger targets an eligible OpenAI-compatible model source,
the proxy SHALL run synthetic source compaction and SHALL return the same
single-item compact SSE lifecycle required by Codex. The completed item MUST
contain a codex-lb-owned `clb1:` compaction envelope. The proxy MUST NOT return
a successful compaction lifecycle for an incomplete, truncated, malformed, or
empty source summary. A completed top-level response MUST NOT override a
truncation finish reason, non-empty `incomplete_details`, or an incomplete
message item.

Before any later upstream request, the proxy SHALL lower a valid `clb1:` replay
item into explicit summary context and SHALL NOT forward the proxy-owned
envelope as native encrypted state. A malformed `clb1:` item MUST become an
explicit unavailable-history note.

#### Scenario: Foreign plaintext reasoning is accepted by native Responses

- **GIVEN** request input contains a top-level reasoning item with non-empty
  plaintext `content` and an output-only `status`
- **WHEN** an ordinary, compact, WebSocket, HTTP-session bridge, or prepared
  replay request is sent to a native subscription backend
- **THEN** its wire `content` is an empty array and `status` is absent
- **AND** ordinary source Responses replay remains unchanged

#### Scenario: Temporary item IDs are not resolved by stateless upstreams

- **GIVEN** ordinary or compact input contains `rs_tmp_*`, message, or tool item
  IDs and retains a tool `call_id`
- **WHEN** the effective request uses `store: false`
- **THEN** each lookup-only top-level item `id` is absent on the wire
- **AND** the tool `call_id` is preserved
- **AND** an authoritative compaction ID paired with encrypted content remains

#### Scenario: Source compaction emits one proxy-owned item

- **GIVEN** a valid terminal compaction trigger for a source-owned model
- **WHEN** the source completes a non-empty summary
- **THEN** the proxy emits exactly one terminal `compaction` item
- **AND** its `encrypted_content` starts with `clb1:`

#### Scenario: Proxy-owned history is lowered on replay

- **GIVEN** later input contains a valid `clb1:` compaction item
- **WHEN** codex-lb builds any upstream request
- **THEN** the upstream receives explicit summary text instead of the envelope

#### Scenario: Partial or truncated source summary is not installed

- **WHEN** the summarization response is incomplete, truncated, malformed, or
  empty
- **THEN** the proxy returns an error
- **AND** it does not emit a completed compaction item
