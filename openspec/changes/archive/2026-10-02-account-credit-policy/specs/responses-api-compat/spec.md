## ADDED Requirements

### Requirement: Reused upstream websockets recheck account availability
Before forwarding a turn on an existing upstream websocket, the proxy MUST check whether the socket's account is routing-unavailable (paused, deactivated, deleted, or quota-blocked under credit policy `never`). When it is, the proxy MUST retire that upstream socket and route the turn as an account switch: it releases a proxy-injected continuity anchor where that is safe, then connects through normal selection, which either moves the turn to another account or fails closed. If other turns are still pending on the socket, the request MUST be rejected with `account_unavailable` instead of switching.

#### Scenario: Paused account stops serving a live session
- **GIVEN** a downstream websocket whose upstream socket belongs to account A
- **WHEN** account A is paused and the client sends its next turn
- **THEN** the proxy retires A's upstream socket and serves the turn from another eligible account

#### Scenario: Pending turns block the switch
- **GIVEN** account A became unavailable while another turn on its socket is still pending
- **WHEN** a new turn arrives
- **THEN** the proxy rejects it with `account_unavailable`
