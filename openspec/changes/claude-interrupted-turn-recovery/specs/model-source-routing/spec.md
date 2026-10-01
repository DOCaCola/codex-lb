## ADDED Requirements

### Requirement: Settled source Responses stream failures
Source Responses forwarding failures after stream start SHALL settle and release the failed attempt exactly once before delivering one structured error event over HTTP or WebSocket. The event SHALL preserve status and error with only validated Retry-After metadata. The WebSocket SHALL remain usable for later turns. No completion, generation retry or retained successful response SHALL be fabricated. Cancellation MUST remain cancellation.

#### Scenario: Projection failure after output
- **WHEN** a source adapter raises a forwarding failure after delivering assistant text
- **THEN** the client receives a structured error, the request log preserves the failure cause, and no successful response is retained

#### Scenario: Next WebSocket turn
- **WHEN** a source stream fails and the client submits another valid request on the same WebSocket
- **THEN** the next turn can complete without reopening the connection

#### Scenario: Retry metadata
- **WHEN** a stream failure carries a valid Retry-After and unrelated upstream headers
- **THEN** the error event preserves only the validated retry hint, status and error

#### Scenario: Disconnect during output
- **WHEN** the downstream client disconnects before an error or completion
- **THEN** normal cancellation and cleanup apply without sending a synthetic failure or completion
