## ADDED Requirements

### Requirement: Anchored WebSocket turns sent over HTTP carry their full history
When a WebSocket or HTTP bridge `response.create` that carries
`previous_response_id` exceeds the upstream frame budget and is therefore sent
over HTTP, the service SHALL send the turn's verified full-history body without
`previous_response_id` instead. When no verified full history exists, the
service MUST refuse the turn locally before dispatch with
`previous_response_not_found`. The service MUST NOT send
`previous_response_id` to the HTTP backend from this path.

#### Scenario: Oversized follow-up with known history
- **GIVEN** a WebSocket follow-up carries `previous_response_id` and its frame exceeds the upstream frame budget
- **AND** the service holds the verified history of the anchored response
- **WHEN** the turn is sent
- **THEN** the HTTP request carries the full history and no `previous_response_id`

#### Scenario: Oversized follow-up after a reconnect
- **GIVEN** the client reconnects within the same session and sends an oversized anchored follow-up
- **WHEN** the turn is sent
- **THEN** the HTTP request carries the session's verified full history and no `previous_response_id`

#### Scenario: Oversized follow-up with unknown history
- **GIVEN** an oversized anchored follow-up whose anchor the service cannot verify
- **WHEN** the turn is sent
- **THEN** the client receives `previous_response_not_found`
- **AND** no upstream HTTP request is made
