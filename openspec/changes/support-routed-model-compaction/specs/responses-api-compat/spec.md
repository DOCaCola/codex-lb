## ADDED Requirements

### Requirement: Codex compaction is destination-aware

When a valid terminal `compaction_trigger` targets a subscription-backed model,
the proxy SHALL preserve the existing native compact flow and synthetic SSE
lifecycle. Immediately before sending the native compact request, the proxy
MUST replace every non-empty plaintext `content` array on a top-level
`reasoning` input item with an empty array and MUST remove that item's
output-only `status` field. Ordinary non-compact Responses requests MUST NOT
receive this native-boundary sanitation.

When the terminal trigger targets an eligible OpenAI-compatible model source,
the proxy SHALL run synthetic source compaction and SHALL return the same
single-item compact SSE lifecycle required by Codex. The completed item MUST
contain a codex-lb-owned `clb1:` compaction envelope. The proxy MUST NOT return
a successful compaction lifecycle for an incomplete, malformed, or empty
source summary.

Before any later upstream request, the proxy SHALL lower a valid `clb1:` replay
item into explicit summary context and SHALL NOT forward the proxy-owned
envelope as native encrypted state. A malformed `clb1:` item MUST become an
explicit unavailable-history note.

#### Scenario: Foreign plaintext reasoning is accepted by native compaction

- **GIVEN** compact input contains a top-level reasoning item with non-empty
  plaintext `content` and an output-only `status`
- **WHEN** the request is sent to native subscription compaction
- **THEN** its wire `content` is an empty array and `status` is absent
- **AND** ordinary source Responses replay remains unchanged

#### Scenario: Source compaction emits one proxy-owned item

- **GIVEN** a valid terminal compaction trigger for a source-owned model
- **WHEN** the source completes a non-empty summary
- **THEN** the proxy emits exactly one terminal `compaction` item
- **AND** its `encrypted_content` starts with `clb1:`

#### Scenario: Proxy-owned history is lowered on replay

- **GIVEN** later input contains a valid `clb1:` compaction item
- **WHEN** codex-lb builds any upstream request
- **THEN** the upstream receives explicit summary text instead of the envelope

#### Scenario: Partial source summary is not installed

- **WHEN** the summarization response is incomplete, malformed, or empty
- **THEN** the proxy returns an error
- **AND** it does not emit a completed compaction item
