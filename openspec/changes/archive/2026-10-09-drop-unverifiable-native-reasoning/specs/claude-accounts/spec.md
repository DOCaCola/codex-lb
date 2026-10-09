# claude-accounts Delta

## MODIFIED Requirements

### Requirement: Claude history at native Codex dispatch

Native Codex dispatch SHALL authenticate replayed Claude envelopes against the originating client before projecting history. Authenticated Claude thinking and redacted thinking SHALL be omitted, because OpenAI accepts reasoning only as its own encrypted state and refuses to chain onto a response that stored unverifiable reasoning. Claude encryption, signatures, thinking text and foreign lookup identities MUST NOT reach OpenAI. Projection SHALL leave retained logical history, messages, tool call identifiers and paired outputs unchanged. The same policy SHALL apply to HTTP, WebSocket, retained continuation and native compaction.

Native sanitation SHALL forward a `reasoning` item only when it carries non-empty `encrypted_content`; any other reasoning item, including summary-only and plaintext reasoning from another provider, SHALL be omitted. Kept items SHALL have plaintext `content` cleared and output-only `status` removed while their encryption and summary stay intact. Sanitation SHALL remove invalid known item-type ID prefixes without fabricating identities and reject unprojected Claude envelopes. Authenticated Claude-hosted search SHALL follow portable hosted-search history projection. These rules SHALL apply in completed and active turns. Projection diagnostics SHALL count omitted thinking, omitted unverifiable reasoning and projected searches without content. Authentication failures MUST NOT dispatch or penalize an upstream account.

#### Scenario: Opus-to-Sol switch
- **WHEN** a scoped Claude thinking envelope with a resp_msg-prefixed reasoning ID is replayed to native Sol
- **THEN** OpenAI receives the surrounding history without that item, and neither its Claude envelope, its text nor its foreign ID
- **AND** the original retained item remains unchanged

#### Scenario: Chained turn after a switch
- **WHEN** the first native turn after a switch from Claude succeeds and the next turn chains onto it with `previous_response_id`
- **THEN** the stored response contains no reasoning that OpenAI cannot verify

#### Scenario: Tool continuation
- **WHEN** Claude thinking accompanies a complete function/custom-tool call and result pair
- **THEN** native projection preserves their identifiers, arguments and outputs in order

#### Scenario: Tampered or cross-scope envelope
- **WHEN** Claude state is invalid or belongs to another client
- **THEN** the native request fails before upstream dispatch without exposing state contents

#### Scenario: Unrepresentable provider state
- **WHEN** native input contains authenticated Claude redacted thinking
- **THEN** OpenAI receives the surrounding history without that item, the omission is counted, and retained history keeps the original

#### Scenario: Claude hosted search
- **WHEN** native input contains an authenticated Claude search envelope and its `web_search_call`
- **THEN** OpenAI receives one projected assistant text message in their place, and neither the envelope nor the Claude call identity

#### Scenario: Native history stays native
- **WHEN** native reasoning with valid rs-prefixed identity and encrypted content is replayed
- **THEN** its encryption and summary remain intact and no Claude projection occurs

#### Scenario: Foreign plaintext reasoning
- **WHEN** a reasoning item without `encrypted_content` carries a summary or reasoning_text content
- **THEN** native sanitation omits it and counts the omission

#### Scenario: Plaintext reasoning preservation
- **WHEN** a reasoning item with `encrypted_content` also carries reasoning_text content
- **THEN** native sanitation keeps its encryption and existing summary, empties the content array, and does not move the plaintext into the summary
