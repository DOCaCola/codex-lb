## ADDED Requirements

### Requirement: History-preserving translated Claude continuation
Translated Claude requests ending in an assistant message SHALL append one wire-only user `(continue)` turn after validating complete tool results. Existing history and signed blocks MUST remain ordered and unchanged. User-ending requests, native Messages and retained logical history MUST remain unchanged. This transformation MUST NOT relax authentication or resource ownership.

#### Scenario: Retry after assistant progress
- **WHEN** Codex retries an interrupted response with history ending in assistant progress
- **THEN** Claude receives all original history followed by a user continuation rather than assistant prefill
- **AND** no prior message is removed and the synthetic turn is not retained as client input

#### Scenario: Expanded continuation
- **WHEN** previous_response_id expands to completed assistant output with no new input
- **THEN** Claude receives one user continuation after the expanded output

#### Scenario: Unfinished tool call
- **WHEN** the input ends with a tool call lacking its corresponding result
- **THEN** preparation fails before dispatch without fabricating tool output or appending a continuation

#### Scenario: Existing user or tool-result ending
- **WHEN** translated input already ends with user content or a validated tool result
- **THEN** no continuation text is added

#### Scenario: Native request
- **WHEN** a native Messages client submits assistant-tail history
- **THEN** the gateway does not apply this translated-request continuation policy

### Requirement: Bounded undeclared Claude tool diagnostics
Undeclared upstream Claude tools SHALL fail explicitly without alias guessing or client-side execution. Diagnostics SHALL identify source, model, response, content index, declaration count and a bounded name fingerprint; a bounded syntactically safe tool name MAY also be recorded. Arguments, call IDs, conversation contents and credentials MUST NOT be logged.

#### Scenario: Unknown tool after text
- **WHEN** Claude emits an undeclared tool after an assistant progress message
- **THEN** the tool is rejected with content-free identity diagnostics and no tool-call event for that tool reaches the client

#### Scenario: Unsafe name
- **WHEN** the rejected name contains control characters, unsupported characters or excessive length
- **THEN** only its fingerprint and safe structural metadata are logged
