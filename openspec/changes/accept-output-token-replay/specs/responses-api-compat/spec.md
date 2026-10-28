## ADDED Requirements

### Requirement: Native output-token replay include and ciphertext
Responses HTTP and WebSocket requests on `/v1/responses` and
`/backend-api/codex/responses` SHALL accept `output.encrypted_content` in the
include array and forward it unchanged alongside other supported include values.
The service SHALL preserve upstream output-item encrypted_content fields in
streaming events and completed response payloads, and SHALL preserve those fields
when native clients replay messages or tool calls in later requests. Existing
ownership and explicit upstream ciphertext-rejection recovery rules SHALL remain
in force. Supporting output replay MUST NOT accept arbitrary unknown include
values or non-array include values, disable the client's replay capability, or
replace encrypted fields with invented plaintext.

#### Scenario: Updated client requests encrypted output
- **WHEN** a Responses client requests reasoning.encrypted_content and output.encrypted_content
- **THEN** both values reach upstream without a local include validation error
- **AND** upstream message and tool-call ciphertext reaches the client unchanged

#### Scenario: Replay previous output
- **WHEN** a native client resends output messages and tool calls with encrypted_content
- **THEN** their ciphertext is retained in the forwarded input

#### Scenario: Invalid includes remain invalid
- **WHEN** include contains an unsupported value or is not an array
- **THEN** the request fails with400 invalid_request_error and param include before upstream dispatch
