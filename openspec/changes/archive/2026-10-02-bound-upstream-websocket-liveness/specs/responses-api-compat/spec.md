# responses-api-compat Delta

## MODIFIED Requirements

### Requirement: Responses upstream websocket liveness is bounded

The proxy MUST configure direct and routed upstream Responses WebSocket transports with a fixed ping/pong liveness bound that is independent of `proxy_downstream_websocket_idle_timeout_seconds`: a ping every 20 seconds, and the connection declared dead when no inbound frame arrives within 30 seconds of a ping. Any inbound frame, not only the matching pong, MUST count as proof of liveness for the native helper. A transport that exposes only a single heartbeat value MUST be configured so that its pong wait is 30 seconds. A direct connection MUST use the native helper watchdog when native egress is selected and the Python `websockets` watchdog only on the pre-dispatch missing-helper fallback. When an established Responses WebSocket is terminated because its transport did not receive the required pong, the adapter MUST classify the failure as `upstream_websocket_liveness_timeout`. Direct WebSocket and HTTP bridge relay owners MUST treat that failure as account neutral, MUST NOT transparently replay a pending request whose delivery is ambiguous, MUST finalize its pending request ownership exactly once, and MUST retire the affected upstream socket so a later client retry opens a fresh connection. An HTTP bridge reader MUST suppress its own pending-deque settlement only when a concurrent submitter explicitly claimed liveness-settlement ownership under the session lifecycle lock; `session.closed` alone MUST NOT suppress settlement.

#### Scenario: Direct Responses websocket loses pong liveness

- **GIVEN** a direct upstream Responses WebSocket has been established
- **WHEN** the selected native-helper or Python fallback keepalive watchdog terminates it after a pong timeout
- **THEN** the pending request fails with `upstream_websocket_liveness_timeout`
- **AND** the request is not transparently replayed
- **AND** the selected account receives no failure-health signal
- **AND** the affected upstream socket is retired

#### Scenario: Routed Responses websocket loses pong liveness

- **GIVEN** a routed upstream Responses WebSocket has been established for an HTTP bridge or direct WebSocket client
- **WHEN** the native-helper or aiohttp heartbeat watchdog terminates it after a pong timeout
- **THEN** the pending request fails with `upstream_websocket_liveness_timeout`
- **AND** the request is not transparently replayed
- **AND** the selected account receives no failure-health signal
- **AND** the affected upstream socket is retired

#### Scenario: Silent upstream connection is detected within the bound

- **GIVEN** an upstream Responses WebSocket stops delivering frames and answering pings
- **WHEN** 30 seconds pass after the next ping without an inbound frame
- **THEN** the transport is declared dead with `upstream_websocket_liveness_timeout`
- **AND** the downstream idle timeout does not extend that bound

#### Scenario: Streaming output keeps the connection alive

- **GIVEN** an upstream Responses WebSocket is streaming output frames
- **WHEN** a pong is delayed behind that output beyond the pong timeout
- **THEN** the native helper keeps the upstream socket open because inbound frames prove liveness

#### Scenario: Long turn remains healthy through control frames

- **GIVEN** a Responses turn emits no application event within the liveness interval
- **WHEN** the upstream WebSocket continues replying to transport pings
- **THEN** the proxy keeps the upstream socket open
- **AND** the existing Responses request budget remains authoritative for the turn

#### Scenario: Closed bridge without a sender claim later loses pong liveness

- **GIVEN** an HTTP bridge session has multiple pending requests
- **AND** a separate submit failure marks the session closed without claiming liveness-settlement ownership
- **WHEN** the still-running upstream transport later expires its heartbeat
- **THEN** the reader settles every pending request with `upstream_websocket_liveness_timeout`
- **AND** the selected account receives no failure-health signal

#### Scenario: Claimed bridge settlement survives submitter cancellation

- **GIVEN** an HTTP bridge submitter claims liveness-settlement ownership after its send fails
- **WHEN** the submitter is cancelled before whole-deque settlement completes
- **THEN** settlement continues until every pending sibling is finalized exactly once
- **AND** the submitter cancellation is preserved after settlement completes

#### Scenario: Dashboard idle timeout controls new connections

- **GIVEN** `CODEX_LB_PROXY_DOWNSTREAM_WEBSOCKET_IDLE_TIMEOUT_SECONDS=120` and an operator stores `45` through `PUT /api/settings`
- **WHEN** a new downstream WebSocket connection is accepted on any replica
- **THEN** its idle timeout uses 45 seconds
- **AND** its upstream WebSocket keeps the fixed 30-second pong bound
- **AND** connections accepted before the change keep the idle value they were bound with
