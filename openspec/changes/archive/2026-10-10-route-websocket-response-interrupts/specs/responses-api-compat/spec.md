## ADDED Requirements

### Requirement: Codex WebSocket response interrupts reach only the in-flight response

When a downstream Responses WebSocket client sends `response.interrupt`, the
service SHALL deliver it only to the pending response whose client-visible
response ID matches `response_id`. For a turn relayed over the upstream
WebSocket, the service SHALL forward the frame addressed to that response's
upstream response ID. For a turn relayed over HTTP, the service SHALL cancel
the HTTP stream and end the turn with `response.incomplete` whose
`incomplete_details.reason` is `interrupted` and whose `output` holds the
output items already completed. An interrupt naming no in-flight response,
including one sent before any upstream connection exists, SHALL be consumed
without an upstream frame or a client error. Upstream events naming a
response that already reached its terminal event on the connection SHALL NOT
be delivered or attributed to another pending request.

#### Scenario: Interrupt crossing the terminal event is consumed

- **GIVEN** a response that has already emitted `response.completed`
- **WHEN** the client sends `response.interrupt` naming that response
- **THEN** no frame is sent upstream and the client receives no error
- **AND** the client's next turn is unaffected

#### Scenario: Interrupt before any upstream connection

- **WHEN** the client sends `response.interrupt` before its first turn
- **THEN** the frame is consumed without a 400 error

#### Scenario: WebSocket turn is interrupted upstream

- **GIVEN** an in-flight response relayed over the upstream WebSocket
- **WHEN** the client sends `response.interrupt` naming its client-visible ID
- **THEN** the frame is forwarded upstream with the upstream response ID

#### Scenario: HTTP-relayed turn is interrupted locally

- **GIVEN** an in-flight response relayed over HTTP
- **WHEN** the client sends `response.interrupt` naming it
- **THEN** the HTTP stream is cancelled
- **AND** the client receives `response.incomplete` with reason `interrupted`
  and the output items already completed

#### Scenario: Late event of a finished response is not misattributed

- **GIVEN** a response that has reached its terminal event and a later pending request
- **WHEN** upstream emits another event naming the finished response
- **THEN** the event is dropped and the pending request's events are unaffected

### Requirement: Interrupted responses anchor the follow-up turn

A Responses WebSocket response that ends with `response.incomplete` whose
`incomplete_details.reason` is `interrupted` SHALL anchor a follow-up
`previous_response_id` like a completed response: its owner SHALL be
remembered, and the persisted owner lookup SHALL accept its request log.
Cancelled request logs with any other error code SHALL NOT anchor a follow-up.

#### Scenario: Follow-up continues from the interrupted response

- **GIVEN** a response interrupted by the client
- **WHEN** the client's next turn sets `previous_response_id` to that response
- **THEN** the owner lookup returns the interrupted response's account

## MODIFIED Requirements

### Requirement: WebSocket incomplete responses preserve the upstream reason in request logs

When an upstream Responses WebSocket terminal `response.incomplete` event contains a non-empty string at `response.incomplete_details.reason`, the service SHALL preserve that reason as both `error_code` and `error_message` in the request log. The request log status SHALL be `cancelled` when the reason is `interrupted`, because the client stopped the response, and `error` for every other reason. The terminal event sent to the downstream client and the account-health treatment of an incomplete response SHALL remain unchanged.

#### Scenario: max-output limit is identifiable in a WebSocket request log

- **WHEN** the upstream emits `response.incomplete` with
  `incomplete_details.reason` equal to `max_output_tokens`
- **THEN** the corresponding WebSocket request log has status `error`,
  `error_code` equal to `max_output_tokens`, and `error_message` equal to
  `max_output_tokens`
- **AND** the account is not marked unhealthy solely because of that
  incomplete event

#### Scenario: client interrupt is a cancellation in a WebSocket request log

- **WHEN** the upstream emits `response.incomplete` with
  `incomplete_details.reason` equal to `interrupted`
- **THEN** the corresponding WebSocket request log has status `cancelled`
  and `error_code` equal to `interrupted`
- **AND** the account is not marked unhealthy because of that incomplete event
