## ADDED Requirements

### Requirement: Responses admission has a bounded instance budget

The service MUST use `CODEX_LB_RESPONSES_BODY_LIMIT_BYTES` for raw and decoded admission on `/v1/responses`, `/backend-api/codex/responses`, their `/compact` operations, and `/internal/bridge/responses`, including canonicalized aliases, trailing slashes, and mounted paths. The default MUST be 128 MiB and configuration MUST be an integer from 32 through 512 MiB inclusive; invalid configuration MUST fail startup. Changes MUST require restart. The default downstream WebSocket allowance and expanded replay guards MUST use the same configured budget. Explicit listener overrides MUST retain their existing precedence. Unrelated routes MUST retain their existing budgets.

#### Scenario: Large history admitted for compaction

- **WHEN** a Responses or compact history fits a configured 256 MiB budget but exceeds 128 MiB
- **THEN** neither raw nor decoded admission rejects it under the old fixed budget
- **AND** admission preserves the entire request content

#### Scenario: Local refusal is distinguishable

- **WHEN** Responses ingress exceeds its configured budget
- **THEN** it returns HTTP 413 with `inbound_body_too_large`, identifies codex-lb and the budget, and distinguishes declared lengths from observed lower bounds
- **AND** expanded replay refusals use `outbound_body_too_large` rather than asserting an upstream context verdict

## MODIFIED Requirements

### Requirement: HTTP ingress reuses existing budgets

The service MUST use the fixed general HTTP body budget (`MAX_DECOMPRESSED_BODY_BYTES`, 32 MiB, in `app/core/ingress_limits.py`) as the general raw and decompressed HTTP request-body budget. Responses and compact operations MUST instead use the configured Responses instance budget, default 128 MiB. The general budget MUST remain fixed.

Route-specific budget and error-envelope selection MUST use the application-relative route path after removing any matching ASGI `root_path` prefix.

The generic guard MUST apply to requests solely because they declare `multipart/form-data`; the client-declared media type MUST NOT grant an exemption. An owning route capability MAY define an exact method/path-scoped authorization-before-read contract and dedicated bounded multipart parser. Only unencoded multipart requests to that exact operation, or requests marked by its outer content-encoding gate, MAY bypass generic admission. The gate MUST identify its operation independently of the declared media type, remove the encoding and mark the scope as handled without consuming the body, and the exception MUST NOT apply to any other operation.

#### Scenario: Another HTTP path uses the general budget

- **WHEN** a guarded request targets any other HTTP path
- **THEN** its raw and decompressed HTTP ingress budget is the fixed 32 MiB general budget

#### Scenario: Route-owned unencoded multipart uses dedicated admission

- **GIVEN** an exact operation has a capability-defined authorization-before-read contract and dedicated bounded multipart parser
- **WHEN** an unencoded request to that operation declares media type `multipart/form-data`
- **THEN** the generic raw whole-body guard does not preempt operation authorization or its dedicated parser limit

#### Scenario: Unrelated unencoded multipart remains guarded

- **WHEN** an unencoded request outside a route-owned multipart operation declares media type `multipart/form-data`
- **THEN** the service applies the generic raw-body budget
- **AND** the declared media type alone does not bypass admission

#### Scenario: Encoded multipart remains guarded

- **WHEN** a `multipart/form-data` request outside a route-owned multipart exception carries a `Content-Encoding` header
- **THEN** the service applies both the raw and decompressed budget checks

#### Scenario: Route-owned multipart admission can preserve authorization precedence

- **GIVEN** an exact operation has a capability-defined outer content-encoding gate, authorization-before-read contract, and dedicated bounded multipart parser
- **WHEN** an encoded request targets that operation, regardless of its declared media type
- **THEN** the generic raw and decompressed-body guards do not preempt operation authorization or its dedicated parser limit
- **AND** encoded multipart requests to all other operations remain guarded

#### Scenario: Mounted Responses route keeps its route-specific policy

- **GIVEN** the service is mounted under a non-empty ASGI `root_path`
- **WHEN** the request scope path includes that prefix and targets `/v1/responses` relative to the application
- **THEN** the service applies the Responses-specific ingress budget
- **AND** any ingress failure uses the OpenAI-compatible error envelope

### Requirement: HTTP ingress failures use the path-family error envelope

Ingress failures on `/v1/*`, `/backend-api/*`, `/api/codex/*`, and `/internal/bridge/*` MUST use an OpenAI-compatible error envelope with `type = invalid_request_error`. Equivalent paths MUST be classified after the existing outer path canonicalization. Other ingress paths MUST retain the dashboard-compatible error envelope. Oversized Responses and compact requests MUST use `code = inbound_body_too_large`; other oversized requests MUST retain `code = payload_too_large`. Malformed or unsupported compression MUST use `code = invalid_request_error` on OpenAI paths and `code = invalid_request` on other paths.

#### Scenario: OpenAI path rejects an oversized body

- **WHEN** a raw or decompressed request body on an OpenAI-compatible proxy path exceeds its budget
- **THEN** the service returns HTTP 413
- **AND** the response has OpenAI error `code = inbound_body_too_large` on Responses/compact operations, otherwise `payload_too_large`, and `type = invalid_request_error`

#### Scenario: OpenAI path rejects invalid compression

- **WHEN** a request on an OpenAI-compatible proxy path uses unsupported or malformed compression
- **THEN** the service returns HTTP 400
- **AND** the response has OpenAI error `code = invalid_request_error` and `type = invalid_request_error`

#### Scenario: Dashboard settings path rejects an oversized body

- **WHEN** a raw or decompressed request body on `/api/settings` exceeds its budget
- **THEN** the service returns HTTP 413
- **AND** the response has dashboard error `code = payload_too_large`

#### Scenario: Dashboard settings path rejects invalid compression

- **WHEN** a request on `/api/settings` uses unsupported or malformed compression
- **THEN** the service returns HTTP 400
- **AND** the response has dashboard error `code = invalid_request`

#### Scenario: Duplicated Codex alias is classified after canonicalization

- **WHEN** an ingress failure targets `/backend-api/codex/v1/responses/`
- **THEN** the service applies the same Responses budget and OpenAI-compatible envelope as `/backend-api/codex/responses/`
