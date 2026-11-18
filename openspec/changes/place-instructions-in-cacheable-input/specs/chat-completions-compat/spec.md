## REMOVED Requirements

### Requirement: Map chat requests to Responses wire format

**Reason**: `system`/`developer` messages are no longer merged into top-level `instructions`, so the JSON-mode exception has nothing left to preserve. The requirement is replaced by "Map chat requests to cacheable Responses input" below. "Tool choice values" carries over unchanged; "System message normalization" is restated; "JSON object response format preserves instruction-role messages" becomes "JSON object response format keeps instruction messages in context".

**Migration**: none. Clients send the same requests.

## ADDED Requirements

### Requirement: Map chat requests to cacheable Responses input

The service MUST map `system` and `developer` chat messages to `developer` input messages in their original position and all other messages to `input`. A client's top-level `instructions` MUST pass through unchanged. Tool definitions MUST be normalized to the Responses tool schema, and `tool_choice`, `reasoning_effort`, and `response_format` MUST be mapped consistently. Unsupported fields MUST not be silently ignored if they change behavior.

#### Scenario: System message normalization
- **WHEN** the client sends a `system` message followed by a `user` message
- **THEN** the mapped `input` starts with a `developer` message carrying the system content, followed by the user message
- **AND** the mapped `instructions` is `""`

#### Scenario: Later system message keeps its position
- **WHEN** a `system` message follows earlier user and assistant messages
- **THEN** the mapped `input` carries it as a `developer` message at that position

#### Scenario: JSON object response format keeps instruction messages in context
- **WHEN** the client sends `response_format: {"type":"json_object"}` with a `system` or `developer` message that instructs JSON output
- **THEN** the mapped Responses payload keeps that message in `input` as a `developer` message
- **AND** the mapped `instructions` value does not contain that message content

#### Scenario: Tool choice values
- **WHEN** the client sets `tool_choice` to `none`, `auto`, or `required`
- **THEN** the service forwards the value consistently in the mapped Responses request

