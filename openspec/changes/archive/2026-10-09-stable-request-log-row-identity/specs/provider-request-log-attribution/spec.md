## ADDED Requirements

### Requirement: Provider error classification
Request logs for failed model-source requests SHALL record the upstream error's `code` when present and otherwise its `type`, so provider errors that carry only a type (such as Anthropic `overloaded_error`) are classified. Client-facing error responses SHALL remain unchanged.

#### Scenario: Anthropic overload
- **WHEN** Anthropic refuses a request with `{"error":{"type":"overloaded_error"}}`
- **THEN** the request-log row's error code is `overloaded_error`
