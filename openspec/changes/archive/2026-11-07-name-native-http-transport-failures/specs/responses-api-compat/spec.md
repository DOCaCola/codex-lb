## ADDED Requirements

### Requirement: Native HTTP transport failures are attributed on the request log
When a native HTTP upstream exchange fails before a terminal event, the
service SHALL record `failure_phase` and a `failure_detail` naming the
error by kind or variant only on that turn's request log. A WebSocket turn sent
over HTTP MUST be logged with `upstream_transport` `http`, and its client
frame MUST NOT carry the internal synthetic-failure marker.

#### Scenario: Origin closes before the response
- **GIVEN** the native helper's HTTP origin closes the connection before sending a response
- **WHEN** the helper reports the failure
- **THEN** its error event names phase `request` and detail `hyper_incomplete_message`

#### Scenario: Oversized WebSocket turn fails over HTTP
- **GIVEN** a WebSocket turn larger than the frame budget is sent over HTTP
- **AND** the HTTP exchange fails with a named transport error
- **WHEN** the client receives `response.failed`
- **THEN** the frame carries no internal synthetic-failure marker
- **AND** the request log records `upstream_transport` `http` with the failure's phase and detail
