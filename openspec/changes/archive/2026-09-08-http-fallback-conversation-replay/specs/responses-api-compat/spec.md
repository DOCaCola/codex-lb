## ADDED Requirements

### Requirement: Local replay of stateless HTTP fallback responses
The proxy MUST retain complete input and completed output for scoped direct-WebSocket turns served over stateless HTTP. It MUST scope replay by API key and conversation, reconstruct incremental follow-ups before policy validation, and omit the ephemeral previous response id upstream. Failed, compaction, and unresolved incremental requests MUST NOT seed replay state. When the client carries the complete retained prefix including an identified provider output item, the proxy MUST NOT prepend that history again. Content equality of repeated user messages alone MUST NOT authorize deduplication. Native WebSocket response chaining MUST remain unchanged. Reconstructed requests MUST pass current model, file, account, and capability policy checks.

#### Scenario: Incremental follow-up after HTTP completion
- **WHEN** a client references its retained HTTP response with new input
- **THEN** upstream receives the retained input, completed output, and new input exactly once without previous_response_id

#### Scenario: Missing continuation
- **WHEN** an HTTP response is known but its scoped replay state is unavailable
- **THEN** the proxy requests full-history recovery before upstream dispatch and never sends a context-free delta

### Requirement: Bounded private continuation storage
Replay state MUST expire after one hour without read-based renewal, survive ordinary process restarts, and be limited to 1000 entries, 64 MiB of resident serialized entries, 256 MiB per entry, and 1 GiB aggregate retained files. Publication MUST be atomic, integrity checked on load, and file permissions private. Expired entries MUST never replay and MUST be reclaimed on cache access and periodic per-replica maintenance. Cache read/write failures MUST preserve client recovery and completion settlement. Cross-key and cross-conversation requests MUST NOT read retained content.

#### Scenario: Restart and eviction
- **WHEN** the process restarts with valid cache files
- **THEN** unexpired scoped entries remain available and expired or evicted entries require client replay
