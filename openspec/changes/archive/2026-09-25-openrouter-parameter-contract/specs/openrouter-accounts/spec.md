## ADDED Requirements

### Requirement: OpenRouter parameter capabilities govern projection
The system MUST retain synchronized supported parameters and advertise parallel-tool support only when tools and the parallel-tool parameter are supported. Unsupported `parallel_tool_calls: true` MUST be omitted; explicit unsupported `false` MUST return a clear unsupported-parameter error. Strict parameter routing and exact model identity MUST be preserved. Reasoning choices MUST be sorted in ascending effort without changing the supported set or default.

#### Scenario: Tool-only endpoint
- **WHEN** a model supports tools but not the parallel-tool parameter
- **THEN** permissive parallel hints are omitted and explicit serial constraints are rejected before dispatch

#### Scenario: Reversed provider efforts
- **WHEN** the provider lists xhigh, medium, low
- **THEN** clients receive low, medium, xhigh with the original default

### Requirement: OpenRouter errors conform to client error contracts
OpenRouter HTTP rejections MUST preserve their HTTP status and message while exposing string error codes and types to clients. WebSocket clients MUST receive a parseable terminal error rather than wait for a completion that will never arrive.

#### Scenario: Numeric provider error code
- **WHEN** OpenRouter rejects a WebSocket-backed turn with HTTP 404 and numeric code 404
- **THEN** the client receives an error frame with status 404 and a string code and the original message
