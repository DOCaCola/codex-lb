## ADDED Requirements

### Requirement: Idle client Responses WebSockets are reclaimed only under capacity pressure

The proxy MUST NOT close a client Responses WebSocket because it has been quiet for some time. Codex keeps one socket per thread across turns and chains each request onto the previous response on that socket, so a quiet socket is a client between turns or running tools. When a new proxy WebSocket handshake finds the WebSocket admission lane full, the proxy MUST ask the least recently used idle client Responses WebSocket to close and MUST admit the handshake once the released slot is free, waiting at most a bounded time before returning the existing `429` lane-overload response. Each full-lane handshake reclaims at most one socket and never one already asked to close. A socket is idle only when it has no pending request, no unfinished terminal settlement, and no client tool calls awaiting results: after a response completes with client-executed calls (`function_call`, `custom_tool_call`, `apply_patch_call`) the socket stays protected until the client sends its next request. The reclaimed socket MUST re-verify idleness under its send lock, drain a frame already buffered at the boundary, and close with code 1001 and reason `Idle Responses websocket reclaimed`; a client frame arriving first cancels the reclaim. Other proxy WebSockets (realtime and live relays) are never reclaimed. No setting controls this behaviour.

#### Scenario: Quiet socket stays open below capacity

- **GIVEN** a client Responses WebSocket whose last response completed several minutes ago
- **WHEN** the WebSocket lane still has free slots
- **THEN** the proxy keeps the socket open
- **AND** the client's next request continues on the same socket

#### Scenario: Full lane reclaims the least recently used idle socket

- **GIVEN** the WebSocket lane is full and two client Responses WebSockets are idle
- **WHEN** a new proxy WebSocket handshake arrives
- **THEN** the idle socket with the oldest activity closes with code 1001 and reason `Idle Responses websocket reclaimed`
- **AND** the new handshake is admitted on the released slot
- **AND** the other idle socket stays open

#### Scenario: Client tool execution protects the socket

- **GIVEN** a client Responses WebSocket whose last response completed with a `function_call`
- **AND** the client has not yet sent the call's output
- **WHEN** a full-lane handshake looks for an idle socket
- **THEN** that socket is not reclaimed

#### Scenario: No idle socket keeps the overload response

- **GIVEN** the WebSocket lane is full and every client Responses WebSocket has a pending request or owed tool results
- **WHEN** a new proxy WebSocket handshake arrives
- **THEN** the handshake receives the existing `429` lane-overload response
- **AND** no socket is closed

