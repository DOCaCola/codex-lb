## ADDED Requirements

### Requirement: Native HTTP Responses request compression

The service MUST encode every native ChatGPT-account HTTP `/responses` body with zstd level 3, without a size or compression-ratio threshold, for both Python and native egress. It MUST set Content-Encoding to `zstd`, Content-Type to `application/json`, and Content-Length to the compressed byte length. Compression MUST run off the event loop and prepared bytes MUST be reused by transport retries of that prepared request. It MUST reject a pre-existing Content-Encoding at preparation and MUST remove client-supplied encoding headers before preparing upstream headers. Payload tracing, size limits, and transport selection MUST use uncompressed JSON. Compression measurements MUST be logged at DEBUG.

#### Scenario: Native HTTP request including compaction turns
- **WHEN** a native ChatGPT account sends an HTTP `/responses` turn, including a compaction turn or a frame-size WebSocket fallback
- **THEN** the upstream receives a zstd body that decodes to the exact prepared JSON and matching content headers
- **AND** overridden upstream base URLs retain the same behavior

#### Scenario: Other providers and transports stay unchanged
- **WHEN** an upstream request uses a model source, a WebSocket frame, `/responses/compact`, or another endpoint
- **THEN** this HTTP Responses compression policy does not apply

#### Scenario: Compression or upstream rejection fails normally
- **WHEN** compression fails or upstream rejects a compressed body with 400 or 415
- **THEN** the failure is surfaced through the normal error path
- **AND** the service does not retry with an uncompressed body
