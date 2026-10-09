## ADDED Requirements

### Requirement: WebSocket connection-limit terminals are reconnects

When an upstream Responses WebSocket terminates a request with
`error_code='websocket_connection_limit_reached'`, the request-log producer
MUST persist the row with `status='cancelled'` and keep that error code, so
that it is excluded from every error count, error rate and top error. This
classification MUST NOT apply to any other error code, and MUST NOT change
account health or selection. Rows persisted earlier remain unchanged.

#### Scenario: Connection-limit terminal is not an error

- **GIVEN** an upstream WebSocket frame with code `websocket_connection_limit_reached`
- **WHEN** the request log is written
- **THEN** the row has `status='cancelled'` and `error_code='websocket_connection_limit_reached'`
- **AND** the window's error count excludes it

#### Scenario: Other WebSocket failures remain errors

- **GIVEN** an upstream WebSocket frame with code `previous_response_not_found`
- **WHEN** the request log is written
- **THEN** the row has `status='error'`

## MODIFIED Requirements

### Requirement: Cancelled request logs remain visible and distinct

The Request Logs operator surface MUST include persisted
`status='cancelled'` rows in its unfiltered listing and total. Cancelled rows
with `error_code='websocket_connection_limit_reached'` MUST be exposed with
public status `reconnect`; all other cancelled rows MUST be exposed with
public status `cancelled`. Each public status MUST be available through its
own status option and filter, neither MUST be returned by the other's filter,
and neither MUST be returned by the `error` status filter. The dashboard MUST
render each status with localized copy and a visual treatment distinct from
error.

#### Scenario: Unfiltered Request Logs include cancellations

- **GIVEN** one persisted cancelled request and one persisted genuine error
- **WHEN** an operator requests the unfiltered Request Logs list
- **THEN** both requests are returned and included in the total
- **AND** the cancelled request exposes public status `cancelled`

#### Scenario: Cancelled and error filters remain separate

- **GIVEN** one persisted cancelled request and one persisted genuine error
- **WHEN** an operator filters Request Logs by `cancelled`
- **THEN** only the cancelled request is returned
- **AND WHEN** the operator filters Request Logs by `error`
- **THEN** only the genuine error is returned

#### Scenario: Reconnects are listed and filtered separately

- **GIVEN** one persisted connection-limit row, one persisted ordinary cancelled row and one persisted genuine error
- **WHEN** an operator filters Request Logs by `reconnect`
- **THEN** only the connection-limit row is returned, with public status `reconnect`
- **AND WHEN** the operator filters by `cancelled`
- **THEN** only the ordinary cancelled row is returned
- **AND** the status options list `reconnect`, `cancelled` and `error`

#### Scenario: Dashboard presents a cancelled status

- **GIVEN** Request Logs contain a persisted cancelled request
- **WHEN** the dashboard loads status options and renders the request
- **THEN** the status filter includes a localized Cancelled option
- **AND** the row and request details use the localized cancelled label
- **AND** the cancelled badge is visually distinct from the error badge

#### Scenario: Dashboard presents a reconnect status

- **GIVEN** Request Logs contain a persisted reconnect
- **WHEN** the dashboard loads status options and renders the request
- **THEN** the status filter includes a localized Reconnect option
- **AND** the row and request details use the localized reconnect label
- **AND** the reconnect badge is visually distinct from the error badge
