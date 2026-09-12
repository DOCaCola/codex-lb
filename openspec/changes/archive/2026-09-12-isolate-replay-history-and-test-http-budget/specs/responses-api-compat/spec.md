## ADDED Requirements

### Requirement: Replay snapshots own their nested history
Complete input retained for HTTP fallback replay MUST be independently copied after retained-history expansion and before request normalization. Later normalization or mutation of the incoming or forwarded request MUST NOT alter the retained snapshot. Unresolved anchored deltas MUST NOT be represented as complete replay snapshots.

#### Scenario: Normalization mutates a nested directive
- **WHEN** normalized request processing mutates a nested tool definition
- **THEN** the replay snapshot retains the original definition

#### Scenario: Anchor cannot be expanded
- **WHEN** a previous-response anchor has no retained history
- **THEN** its delta is not snapshotted as complete history

### Requirement: Bridge size validation follows the selected transport budget
Requests above the WebSocket frame threshold but within the expanded Responses HTTP budget MUST retain full input and use same-account HTTP transport. Requests above the expanded HTTP budget MUST fail before upstream dispatch with context_length_exceeded, including when synthetic tool output or metadata caused the expansion. A subsequent small turn MAY use WebSocket again. Oversized-request diagnostic dump and deduplication behavior MUST remain independently tested.

#### Scenario: History exceeds the WebSocket threshold
- **WHEN** a bridge turn contains historical inline artifacts above the WebSocket frame threshold
- **THEN** HTTP receives the complete history without destructive slimming

#### Scenario: Injected output exceeds the HTTP budget
- **WHEN** injecting an interrupted tool output exceeds the expanded HTTP request budget
- **THEN** the proxy rejects the turn before dispatch and releases its reservation
