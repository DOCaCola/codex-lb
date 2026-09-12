## MODIFIED Requirements

### Requirement: Downstream websocket ingress accepts large response.create messages
The server MUST accept client-to-proxy websocket messages on the Responses websocket routes (`/backend-api/codex/responses`, `/v1/responses`) up to a configurable ingress budget before closing the connection at the protocol layer. The default listener budget MUST follow `CODEX_LB_RESPONSES_BODY_LIMIT_BYTES` (128 MiB when unset), matching the HTTP Responses decoded-body cap. The `--ws-max-size` CLI flag and `UVICORN_WS_MAX_SIZE` environment variable MUST retain their explicit listener-only overrides, with the CLI flag taking precedence. The server MUST continue to negotiate `permessage-deflate` on the client-facing websocket, and the ingress budget MUST apply to the decompressed message size.

#### Scenario: Oversized response.create reaches the application-level guard
- **WHEN** a client sends a single websocket text message larger than 16 MiB but within the configured ingress budget
- **THEN** the server delivers the message to the application layer instead of closing the connection with `1009 message too big`
- **AND** the application-level oversized-`response.create` handling selects upstream HTTP while preserving the downstream WebSocket

#### Scenario: Operator overrides the ingress budget
- **WHEN** the operator starts the server with `--ws-max-size <bytes>` or sets `UVICORN_WS_MAX_SIZE=<bytes>`
- **THEN** the websocket ingress message budget uses the configured value
- **AND** an invalid (non-positive or non-integer) value fails startup with a clear error

### Requirement: Oversized response.create payloads select HTTP before upstream send

The service MUST measure the final serialized response.create frame, including injected metadata, before sending it upstream. A frame above the configured upstream WebSocket byte budget MUST use upstream HTTP SSE for that turn, even when WebSocket is configured explicitly. The service MUST preserve historical images, tool outputs, and recent input instead of slimming history to meet a transport ceiling. It MUST preserve account ownership, authentication, upstream proxy routing, and continuation fields across this transport selection.

For a downstream WebSocket, the service MUST relay HTTP Responses events on the existing downstream connection using the normal request association and settlement path. It MUST NOT send the oversized frame over WebSocket or replay a dispatched turn merely because a transport closes. A later frame within budget MUST remain eligible for upstream WebSocket.

Expanded request bodies MUST remain bounded by the configured Responses HTTP body budget. Exceeding that budget MUST produce HTTP 400 / outbound_body_too_large before dispatch, identifying a local proxy refusal rather than an upstream context verdict.

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

### Requirement: Responses HTTP ingress uses the expanded bounded budget

HTTP requests to `/v1/responses` and `/backend-api/codex/responses`, and their `/compact` operations, including trailing-slash variants, MUST use `CODEX_LB_RESPONSES_BODY_LIMIT_BYTES` as both the raw-body and decompressed-body ingress budget. The restart-required instance budget MUST default to 128 MiB, accept integer values from 32 to 512 MiB inclusive, and reject invalid configuration at startup. The same budget MUST seed the downstream WebSocket default and bound expanded replay. The unrelated general HTTP budget MUST remain fixed at 32 MiB.

The trailing-slash variants MUST be hidden aliases of the canonical HTTP handlers rather than redirects, so streamed bodies receive the same admission, authorization, and route behavior.

If either representation exceeds that budget, the service MUST stop before route logic or upstream forwarding and return HTTP 413 with an OpenAI-compatible error envelope carrying `error.code = inbound_body_too_large` and `error.type = invalid_request_error`. The error MUST identify codex-lb as the refuser, name the configured budget and configuration key, and distinguish declared lengths from measured lower bounds without exposing request content.

This transport-ingress 413 applies before parsing and is distinct from upstream transport selection. A request that fits the Responses HTTP budget but exceeds the upstream WebSocket byte budget MUST use upstream HTTP without slimming history or asking the client to change transport.

#### Scenario: Larger Responses request fits both ingress checks

- **WHEN** a Responses HTTP request is larger than the general budget but no larger than the Responses budget in either raw or decompressed form
- **THEN** the ingress guards allow the request to continue to Responses route handling

#### Scenario: Trailing-slash Responses request is admitted without redirect

- **WHEN** a client sends a chunked HTTP request to `/v1/responses/` or `/backend-api/codex/responses/`
- **THEN** the service applies the same ingress budget and handler as the corresponding canonical path
- **AND** it does not return a trailing-slash redirect before consuming the guarded body

#### Scenario: Responses raw body exceeds its budget

- **WHEN** a Responses HTTP request's raw body exceeds the Responses budget
- **THEN** the service returns HTTP 413 with `error.code = inbound_body_too_large` and `error.type = invalid_request_error`
- **AND** the service does not invoke Responses route logic or forward the request upstream

#### Scenario: Responses expanded body exceeds its budget

- **WHEN** an encoded Responses HTTP request fits the raw budget but expands beyond the Responses budget
- **THEN** the service returns HTTP 413 with `error.code = inbound_body_too_large` and `error.type = invalid_request_error`
- **AND** the service does not invoke Responses route logic or forward the request upstream

#### Scenario: Oversized HTTP application request reaches the HTTP upstream

- **WHEN** a Responses HTTP request fits the raw and decompressed transport-ingress budget
- **AND** its serialized response.create exceeds the upstream WebSocket budget
- **THEN** the proxy forwards it over upstream HTTP without removing historical input

### Requirement: Bridge size validation follows the selected transport budget
Requests above the WebSocket frame threshold but within the configured expanded Responses HTTP budget MUST retain full input and use same-account HTTP transport. Requests above the expanded HTTP budget MUST fail before upstream dispatch with outbound_body_too_large, including when synthetic tool output or metadata caused the expansion. A subsequent small turn MAY use WebSocket again. Oversized-request diagnostic dump and deduplication behavior MUST remain independently tested.

#### Scenario: History exceeds the WebSocket threshold
- **WHEN** a bridge turn contains historical inline artifacts above the WebSocket frame threshold
- **THEN** HTTP receives the complete history without destructive slimming

#### Scenario: Injected output exceeds the HTTP budget
- **WHEN** injecting an interrupted tool output exceeds the expanded HTTP request budget
- **THEN** the proxy rejects the turn before dispatch and releases its reservation
