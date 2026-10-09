## ADDED Requirements

### Requirement: Claude history at native Codex dispatch

Native Codex dispatch SHALL authenticate replayed Claude envelopes against the originating client and conversation before projecting history. Readable Claude thinking SHALL become portable reasoning summary text without forwarding Claude encryption, signatures or foreign lookup identities. Existing summaries and distinct plaintext reasoning SHALL be preserved. Projection SHALL leave retained logical history, messages, tool call identifiers and paired outputs unchanged. The same policy SHALL apply to HTTP, WebSocket, retained continuation and native compaction.

Native sanitation SHALL remove invalid known item-type ID prefixes without fabricating identities, preserve valid native opaque reasoning and reject unprojected Claude envelopes. Redacted thinking and Claude-hosted search/resource state SHALL fail before dispatch with `nonportable_provider_history` and an input path instead of being silently deleted or treated as native state. Authentication failures MUST NOT dispatch or penalize an upstream account.

#### Scenario: Opus-to-Sol switch
- **WHEN** a scoped Claude thinking envelope with empty summary and a resp_msg-prefixed reasoning ID is replayed to native Sol
- **THEN** its readable text becomes summary_text and neither its Claude envelope nor foreign ID reaches OpenAI
- **AND** the original retained item remains unchanged

#### Scenario: Tool continuation
- **WHEN** readable Claude thinking accompanies a complete function/custom-tool call and result pair
- **THEN** native projection preserves their identifiers, arguments and outputs in order

#### Scenario: Tampered or cross-scope envelope
- **WHEN** Claude state is invalid or belongs to another client or conversation
- **THEN** the native request fails before upstream dispatch without exposing state contents

#### Scenario: Unrepresentable provider state
- **WHEN** native input contains authenticated redacted thinking or Claude-hosted search state
- **THEN** it returns nonportable_provider_history at the affected input index and retains the original data

#### Scenario: Native history stays native
- **WHEN** native reasoning with valid rs-prefixed identity and encrypted content is replayed
- **THEN** its encryption remains intact and no Claude projection occurs

#### Scenario: Plaintext reasoning preservation
- **WHEN** a reasoning item carries both an existing summary and distinct reasoning_text content
- **THEN** native sanitation retains both texts as summaries and empties the content array
