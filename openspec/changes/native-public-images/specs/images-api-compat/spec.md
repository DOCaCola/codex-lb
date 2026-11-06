## MODIFIED Requirements

### Requirement: OpenAI-compatible image edit endpoint

The system SHALL expose `POST /v1/images/edits` and accept the OpenAI Images Edits multipart shape: repeatable `image` / `image[]` file parts, an optional `mask` file part and text fields. The endpoint MUST apply the same model gating as `/v1/images/generations` and MUST express the request in the native JSON shape: source images in their multipart order as `images[].image_url` data URLs, the mask as `mask.image_url`, decimal `n`, `output_compression` and `partial_images` as integers, `stream` of `true` or `false` as a boolean, and every other text field unchanged as a string. A file part without a content type MUST be sent as `image/png`.

#### Scenario: Compatible image edit request returns a JSON envelope

- **WHEN** a client sends multipart `POST /v1/images/edits` with at least one `image` file part, `model=gpt-image-2`, and a non-empty `prompt`
- **THEN** the native edit endpoint receives the images and mask as data URLs in the native JSON shape
- **AND** the client receives the native status and JSON body unchanged

#### Scenario: Unsupported variations endpoint is rejected

- **WHEN** a client sends `POST /v1/images/variations`
- **THEN** the service returns 404 with OpenAI `not_found_error` and a message indicating that variations are not supported

### Requirement: Image routes participate in usage accounting and policy

The system SHALL apply API-key allowed-model policy and model-scoped usage
limits to `/v1/images/*` using the publicly-requested or default
`gpt-image-*` value as the effective model. The request log SHALL record that
model when the row is written. Image usage SHALL settle a limited API-key
reservation exactly once through the tracked image settlement lifecycle, after
the buffered response is returned or the event stream ends. Errors,
cancellation and unavailable usage SHALL release the reservation. Failed or
cancelled finalization SHALL preserve the image response and transfer
ownership to the tracked retrying release fallback.

#### Scenario: API key allowed-model policy blocks gpt-image-2

- **WHEN** an API key's `allowed_models` list does not include `gpt-image-2`
- **THEN** requests to `/v1/images/generations` or `/v1/images/edits` with `model=gpt-image-2` return 403 `model_not_allowed`

#### Scenario: Request log surfaces the publicly requested image model

- **WHEN** an `/v1/images/*` request completes
- **THEN** its `request_logs` row has `model` equal to the publicly requested or default `gpt-image-*` value without a later rewrite

#### Scenario: Failed image-token settlement retains tracked release ownership

- **GIVEN** a limited API key owns a reservation for a successful image generation or edit request
- **WHEN** tracked finalization fails or is cancelled while the reservation remains `reserved`
- **THEN** the image response remains available to the client
- **AND** settlement ownership transfers to a persistence-drained fallback release task
- **AND** transient release failures keep that task tracked and retrying until release succeeds or graceful persistence drain reports timeout
- **AND** a successful fallback restores pre-reserved quota exactly once

#### Scenario: Streamed image usage settles once

- **WHEN** a streamed image request ends after a completed event that reports usage
- **THEN** the API-key reservation is finalized once with that usage
- **AND** a stream that ends without a completed event releases the reservation

### Requirement: Image routes expose bounded operational observability

The system SHALL emit structured route-completion logs and Prometheus metrics for `/v1/images/generations` and `/v1/images/edits`. Observability labels MUST be bounded to route, model, stream flag, HTTP status, and outcome, and MUST NOT include prompts, image bytes, file names, access tokens, or raw upstream payloads. The model label MUST be the effective model when it matches the `gpt-image` model ID shape (family, optional variant, optional dated snapshot), `unknown` when absent and `invalid` otherwise. The duration start time MUST be captured at HTTP ingress, before authentication, body admission, or handler execution, by a pure ASGI middleware that stores it in the request scope state; pre-handler rejections MUST measure duration from that ingress start time. A streamed response MUST record its observation once, when the stream ends, with the stream outcome.

#### Scenario: Successful image request records completion telemetry

- **WHEN** an `/v1/images/generations` or `/v1/images/edits` request completes successfully
- **THEN** the service emits an `images_route_complete` log line with the public image route, public model, stream flag, status, outcome, and duration
- **AND** increments `codex_lb_image_requests_total` and observes `codex_lb_image_request_duration_seconds` with the same bounded labels

#### Scenario: New image model releases keep their label

- **WHEN** a request uses a model such as `gpt-image-2.6-flare`
- **THEN** the model label is that model ID

#### Scenario: Failed image request records completion telemetry

- **WHEN** an image request is rejected by validation or fails upstream
- **THEN** the service emits the same bounded `images_route_complete` fields with a non-success outcome
- **AND** increments the image request counter and duration histogram without logging prompt or binary image content

#### Scenario: Pre-handler rejection measures duration from ingress

- **WHEN** an image route request is rejected before its handler runs (for example an oversized multipart upload or a missing API key)
- **THEN** the recorded duration uses the start time stamped into the request scope state at HTTP ingress
- **AND** non-image HTTP paths and WebSocket scopes receive no such stamp

### Requirement: Native Codex image forwarding

The system SHALL expose `POST /backend-api/codex/images/generations` and
`POST /backend-api/codex/images/edits` as native ChatGPT image endpoints, excluded
from OpenAPI, and SHALL serve `/v1/images/generations` and `/v1/images/edits`
for `gpt-image-*` models through the same forwarding path. Requests MUST pass
proxy authorization, required-capability transport denial, public image-model
policy, API-key limits and scoped account admission before dispatch. The
selected ChatGPT account's credentials MUST replace downstream credentials.
Account selection MUST NOT use a Responses host model, the conversation's model
source or a quota-bypassing control fallback.

The system MUST forward the request JSON, including reference image URLs and
unknown native fields, except for applying an enforced/default public image
model. It MUST NOT fetch reference URLs locally, convert requests into
Responses tool calls, fall back to API-credit providers, follow credentialed
redirects, or replay an image POST after dispatch. Only source-proven
pre-dispatch egress failover MAY occur. A buffered response MUST stop before
retaining more than 100 MiB, including when using a configured egress proxy.

The native upstream status and body MUST be returned unchanged when within the
response budget. Safe response headers MUST retain the image request ID and
Retry-After; cookies and hop-by-hop framing headers MUST NOT be forwarded.
Prompts and image bytes MUST NOT appear in upstream payload traces. Request
logs MUST identify the public image model and upstream HTTP status. Missing or
invalid token usage MUST NOT be fabricated. Authoritative image usage MUST
settle API-key reservations through the tracked image settlement lifecycle;
errors, cancellation and unavailable usage MUST release reservations through
tracked cleanup. Account admission leases MUST be released on every exit,
including when a client abandons a stream.

#### Scenario: Native edit is independent of conversation model
- **WHEN** Codex sends an image edit while its conversation uses a model source
- **THEN** the original JSON is sent to a permitted ChatGPT account's native image edit endpoint without selecting a Responses host

#### Scenario: Native failure remains visible
- **WHEN** the upstream image endpoint returns an error status and body
- **THEN** the same status and body reach the client without an image retry or API-credit fallback

#### Scenario: Native success preserves metadata
- **WHEN** upstream returns image bytes, generation IDs and an image request ID
- **THEN** the response bytes and image request ID are preserved for the client

#### Scenario: Scoped admission and cancellation remain safe
- **WHEN** a scoped API-key image request completes, fails or is cancelled
- **THEN** only an assigned eligible account may be used, its admission lease is released, and its reservation has exactly one tracked settlement or release owner

#### Scenario: Native image route rejects unauthenticated requests
- **WHEN** a native image request fails proxy authorization
- **THEN** no upstream image operation is dispatched and existing authentication-error observability is retained

#### Scenario: Public image request uses the native endpoint
- **WHEN** a client sends `/v1/images/generations` or `/v1/images/edits` for a `gpt-image-*` model
- **THEN** the request is dispatched to the matching native image endpoint on an admitted ChatGPT account

### Requirement: Image edit multipart uploads are authorized and bounded

`POST /v1/images/edits` MUST complete its existing proxy authorization dependencies before reading multipart body bytes. It MUST accept at most 16 source-image file parts across `image` and `image[]`, at most one `mask`, no unknown file-part names, no more than 32 text fields of at most 256 KiB each, every individual file smaller than 50,000,000 bytes, fewer than 50,000,000 bytes across all source images and the mask, and a complete multipart body no greater than 64 MiB (67,108,864 bytes).

The service MUST enforce the body limit against both a usable declared `Content-Length` and actual streamed bytes. It MUST enforce file, aggregate-binary, and text limits before retaining crossing bytes, close multipart spools before usage reservation, account selection, base64 conversion, or native image forwarding, and add no new runtime setting.

This route-owned policy MUST take precedence over the generic raw HTTP body budget for `POST /v1/images/edits`. Its exact-path content-encoding gate MUST run outside the generic raw and decompression guards regardless of the declared media type. Requests handled by that gate, and unencoded requests declared as multipart, MUST NOT be rejected by the generic guards before proxy authorization or the dedicated parser applies this capability's body limit. An unencoded request that does not declare multipart remains under generic admission and MAY be rejected there before authorization. This exception MUST NOT change generic ingress behavior for any other operation.

Byte-limit failures MUST return HTTP 413 with OpenAI error `code = payload_too_large` and `type = invalid_request_error`; a known file-part failure MUST set `param = image` or `param = mask`. Multipart syntax, count, and required-field failures MUST retain OpenAI-compatible invalid-request behavior. Every parser rejection MUST emit exactly one bounded image-route observation with HTTP status and `outcome = invalid_request`.

#### Scenario: Unauthorized image edit does not consume the body

- **WHEN** an image-edit request fails the existing proxy API-key authorization
- **THEN** the authentication response is returned before the ASGI request body is consumed
- **AND** no multipart temporary file is created
- **AND** exactly one auth-error route observation is recorded without parsing the multipart body, using bounded pre-parse labels

#### Scenario: Bounded image edit remains compatible

- **WHEN** an authorized image-edit request supplies at least one source image, an optional mask, required text fields, and all parts are within their limits
- **THEN** the service preserves the ordered `image` and `image[]` bytes, content types, mask, and form fields in the native edit request

#### Scenario: Source image count combines canonical and bracketed keys

- **WHEN** the combined number of `image` and `image[]` file parts exceeds 16, the request contains more than one `mask`, or an unknown file-part name is present
- **THEN** the service returns an OpenAI-compatible HTTP 400 invalid-request response
- **AND** no image bytes are base64-encoded or forwarded

#### Scenario: Declared or streamed image-edit body exceeds its limit

- **WHEN** a usable `Content-Length` exceeds 64 MiB or actual streamed multipart bytes cross 64 MiB
- **THEN** the service returns HTTP 413 with OpenAI error `code = payload_too_large` and `type = invalid_request_error`
- **AND** no usage reservation, account selection, base64 conversion, or upstream request occurs

#### Scenario: Image binary limit is exceeded

- **WHEN** one source image or mask reaches 50,000,000 bytes, or their combined binary bytes reach 50,000,000
- **THEN** the service returns HTTP 413 with OpenAI error `code = payload_too_large`, `type = invalid_request_error`, and the applicable `image` or `mask` parameter
- **AND** bytes beyond the applicable limit are not retained in a spool or handler buffer

#### Scenario: Image text-field resources are bounded

- **WHEN** an image-edit request exceeds 32 text fields or 256 KiB in any text part
- **THEN** the service rejects the request with the documented OpenAI-compatible count or byte-limit response
- **AND** it records one invalid-request route observation without invoking image-edit route logic

#### Scenario: Compressed image edit is rejected without prebuffering

- **GIVEN** image edit has passed proxy authorization
- **WHEN** it declares a non-identity `Content-Encoding`
- **THEN** the service returns HTTP 400 with OpenAI error `code = invalid_request_error` and `type = invalid_request_error` before reading the request body
- **AND** a no-op `identity` encoding is handled as an ordinary multipart request governed by the 64 MiB dedicated body limit
- **AND** exactly one invalid-request route observation is recorded without parsing the multipart body

#### Scenario: Generic ingress does not preempt encoded image-edit authorization

- **GIVEN** an image-edit request fails proxy authorization
- **WHEN** it declares a non-identity `Content-Encoding` and a `Content-Length` greater than the generic raw HTTP budget
- **THEN** the existing authentication response is returned instead of a generic HTTP 413 or encoded-body HTTP 400
- **AND** the request body is not consumed
- **AND** exactly one auth-error route observation is recorded

#### Scenario: Image-edit cleanup preserves transport failures

- **WHEN** parsing succeeds, fails a limit, encounters malformed multipart, receives a client disconnect, or is cancelled
- **THEN** every created multipart spool is closed
- **AND** disconnect and cancellation are not converted to HTTP 413

### Requirement: Native image usage has one accounting owner
Native image requests MUST parse upstream usage once into a request-owned typed record before settlement: from the JSON `usage` of a successful buffered response, or from the `usage` of the completed event of a stream. Both API-key settlement and request logs MUST consume that record's public model, input tokens, output tokens and cached input tokens. Reported usage MUST be persisted even without an API-key reservation so existing request-log pricing can calculate API-equivalent cost. Missing or invalid usage and failed responses MUST NOT fabricate token counts. Raw native response bytes, status, retries and account cleanup MUST remain unchanged.

#### Scenario: Native generation or edit reports usage
- **WHEN** a successful native image response reports input, output and cached input tokens
- **THEN** the request log and applicable API-key settlement use the same counts and the request-log API exposes the existing model-price estimate

#### Scenario: Streamed image reports usage
- **WHEN** a native image stream ends with a completed event that reports usage
- **THEN** the request log and applicable API-key settlement use that usage

#### Scenario: No token usage is available
- **WHEN** upstream omits usage, reports invalid usage or fails the request
- **THEN** request-log token counts remain null and image reservations retain their existing release behavior

## ADDED Requirements

### Requirement: OpenAI-compatible image generation is forwarded natively

The system SHALL expose `POST /v1/images/generations` for the OpenAI Images API JSON request. It MUST require a non-empty `prompt` and a `model` starting with `gpt-image-`, defaulting to the fixed, non-configurable `gpt-image-2`. All other fields MUST be forwarded unchanged and validated upstream, not by local per-model rules.

#### Scenario: Image generation returns the native response

- **WHEN** a client sends `POST /v1/images/generations` with `model=gpt-image-2`, a non-empty `prompt`, and no `stream`
- **THEN** the service returns the native upstream status and JSON body unchanged, with rate-limit headers added

#### Scenario: Non-image model is rejected

- **WHEN** a client sends `POST /v1/images/generations` with `model` not starting with `gpt-image-`
- **THEN** the service returns 400 with OpenAI `invalid_request_error` and `param: model`

#### Scenario: Image parameters are decided upstream

- **WHEN** a client sends `n > 1`, a transparent background, a new quality level, any size, or a field codex-lb does not know
- **THEN** the request reaches the native image endpoint with those values unchanged
- **AND** an upstream rejection reaches the client with its status and body

#### Scenario: Missing model defaults to gpt-image-2

- **WHEN** a client sends `/v1/images/generations` or `/v1/images/edits` without `model`
- **THEN** the service forwards `model=gpt-image-2` and uses it for policy, request log accounting and usage settlement
- **AND** a `CODEX_LB_IMAGES_DEFAULT_MODEL` value in the environment does not change that default (startup logs the removed-setting warning once)

### Requirement: Native image event streams pass through
A successful native `text/event-stream` response SHALL reach the client
unchanged as it arrives. Only terminal events (`error` and `*.completed`)
MAY be decoded, for usage and outcome. Non-streaming and error responses MUST
be buffered and returned unchanged.

#### Scenario: Native events reach the client unchanged
- **WHEN** the native endpoint streams partial-image and completed events
- **THEN** the client receives the same bytes as they arrive and the request log records success with the completed event's usage

#### Scenario: Native stream reports an image error
- **WHEN** the native stream contains an `error` event
- **THEN** the client receives it unchanged and the request log records an error with its code

#### Scenario: Native stream ends early
- **WHEN** the native stream ends without a completed or error event
- **THEN** the request log records `stream_incomplete`

#### Scenario: Upstream connection fails between events
- **WHEN** the upstream connection fails after a complete event
- **THEN** the client receives a final Images `error` event and the request log records the failure

#### Scenario: Upstream connection fails inside an event
- **WHEN** the upstream connection fails while an event is partially sent
- **THEN** the client connection is aborted rather than completed with a truncated event

## REMOVED Requirements

### Requirement: OpenAI-compatible image generation endpoint

**Reason**: Its per-model parameter rules and single-image limit belonged to the Responses tool adapter. Replaced by "OpenAI-compatible image generation is forwarded natively", where the upstream endpoint validates parameters.

**Migration**: Requests the adapter rejected locally, such as `n > 1` or a transparent `gpt-image-2` background, now reach upstream.

### Requirement: Image generation is implemented as a Responses tool adapter

**Reason**: Public image requests are forwarded to the native ChatGPT image endpoint, which supports the full Images API, instead of being translated into a Responses turn that forces one `image_generation` tool call.

**Migration**: None for clients; requests and responses keep the Images API shape. Parameters the adapter rejected locally now reach upstream.

### Requirement: Image generation streaming uses canonical OpenAI Images events

**Reason**: The native endpoint already emits Images streaming events; translating Responses events is no longer needed. See "Native image event streams pass through".

**Migration**: None; clients receive the native Images events.

### Requirement: Internal host selection

**Reason**: Native image forwarding uses no chat host model.

**Migration**: None.

