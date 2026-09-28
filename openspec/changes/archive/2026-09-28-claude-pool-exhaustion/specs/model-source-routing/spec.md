## ADDED Requirements

### Requirement: Source WebSocket retry metadata
Source HTTP errors converted to WebSocket error events SHALL preserve validated Retry-After in a headers object alongside status and error. Credential and unrelated headers MUST NOT be forwarded. The bridge MUST NOT invent successful events or alter status to force client retries.

#### Scenario: Rate-limited source
- **WHEN** a source response returns429 with a valid Retry-After
- **THEN** the WebSocket error retains the status, error and retry header
