## ADDED Requirements

### Requirement: Bounded reversible OpenRouter tool identities
OpenRouter tool names SHALL meet the 64-character ASCII function-name constraint
without changing client-visible names or namespace identities. Declarations,
historical calls and tool choices MUST use consistent deterministic identities.
Streaming and non-streaming Chat and Responses outputs MUST restore original
identities before delivery or replay persistence. Arguments, call IDs and tool
outputs MUST remain unchanged. Native OpenAI and other providers MUST be unaffected.

#### Scenario: Long document tool
- **WHEN** a namespaced MCP document tool exceeds the upstream name limit
- **THEN** its upstream alias fits the limit and the returned call has the original name and namespace

#### Scenario: Replay and selection
- **WHEN** a request selects a tool or replays a historical-only tool call
- **THEN** the same identity receives the same alias regardless of declaration order

#### Scenario: Distinct identities
- **WHEN** tool identities share a flattened spelling or resemble an alias
- **THEN** they remain distinct and restore to their respective original identities

#### Scenario: Streamed tool calls
- **WHEN** an aliased call arrives over arbitrarily chunked SSE
- **THEN** client-visible call events and terminal output restore the original identity
