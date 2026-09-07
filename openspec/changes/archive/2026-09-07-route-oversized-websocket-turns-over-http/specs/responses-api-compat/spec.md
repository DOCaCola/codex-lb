## ADDED Requirements

### Requirement: Oversized response.create payloads select HTTP before upstream send

The service MUST measure the final serialized response.create frame, including injected metadata, before sending it upstream. A frame above the configured upstream WebSocket byte budget MUST use upstream HTTP SSE for that turn, even when WebSocket is configured explicitly. The service MUST preserve historical images, tool outputs, and recent input instead of slimming history to meet a transport ceiling. It MUST preserve account ownership, authentication, upstream proxy routing, and continuation fields across this transport selection.

For a downstream WebSocket, the service MUST relay HTTP Responses events on the existing downstream connection using the normal request association and settlement path. It MUST NOT send the oversized frame over WebSocket or replay a dispatched turn merely because a transport closes. A later frame within budget MUST remain eligible for upstream WebSocket.

Expanded request bodies MUST remain bounded by the Responses HTTP body budget. Exceeding that budget MUST produce context_length_exceeded before dispatch.

#### Scenario: Oversized initial turn uses HTTP without opening an upstream WebSocket

- **WHEN** the initial create frame exceeds the upstream WebSocket budget and fits the HTTP body budget
- **THEN** the proxy sends one upstream HTTP request with the full input
- **AND** HTTP response events reach the existing downstream WebSocket
- **AND** no upstream WebSocket is opened for that turn

#### Scenario: Smaller linked turn retains WebSocket eligibility

- **WHEN** a smaller create follows an HTTP-transport turn on the same downstream connection
- **THEN** it remains eligible for upstream WebSocket
- **AND** the previous_response_id and account ownership are preserved

#### Scenario: Existing WebSocket turn coexists with oversized HTTP turn

- **WHEN** an oversized create arrives while an upstream WebSocket exists
- **THEN** the proxy sends only that create over HTTP
- **AND** both streams retain their response IDs and settle through their original account
- **AND** an upstream WebSocket close does not discard the HTTP turn's terminal event

#### Scenario: Disconnect cancels a backpressured HTTP producer

- **WHEN** the downstream disconnects while an HTTP relay is blocked by backpressure
- **THEN** the proxy cancels and joins the producer and closes its response body
- **AND** its event buffering remains bounded

### Requirement: Provider HTTP payload rejection terminates the Responses turn

For a streaming Responses request, an upstream HTTP 413 MUST produce a terminal response.failed event with error.code context_length_exceeded and error.type invalid_request_error. The proxy MUST NOT pass that rejection back as a retryable transport status or echo the provider's error body. Non-streaming HTTP error contracts MUST remain unchanged.

#### Scenario: HTTP itself rejects the input size

- **WHEN** a streaming upstream HTTP Responses request returns 413
- **THEN** the client receives one terminal context_length_exceeded event
- **AND** the transport adapter does not resend the rejected body

## REMOVED Requirements

### Requirement: Oversized response.create payloads are slimmed or rejected before upstream send

**Reason**: The WebSocket byte ceiling is a transport constraint; valid HTTP input must be preserved.

**Migration**: Use the new per-turn HTTP transport selection requirement. No client or operator setting changes are required.
