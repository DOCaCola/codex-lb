## ADDED Requirements

### Requirement: Translated Claude prompt overflow carries the context length code

When Claude rejects a translated Responses request with `invalid_request_error` whose message begins with
"prompt is too long" and that error has no code, the proxy SHALL return it with `code: context_length_exceeded`,
keeping its status, type and message. Native Messages errors SHALL remain unchanged.

#### Scenario: Translated request exceeds Claude's input limit
- **WHEN** Claude returns HTTP 400 "prompt is too long" for a translated Responses request
- **THEN** the client receives HTTP 400 with `code: context_length_exceeded` and the original message

#### Scenario: Native Messages request exceeds the input limit
- **WHEN** Claude returns the same error for a native Messages request
- **THEN** the client receives Anthropic's error unchanged
