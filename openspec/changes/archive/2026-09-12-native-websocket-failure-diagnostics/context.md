# Operator interpretation

Example warning:
`native_websocket_receive_failed request_id=ws_... failure_phase=consumer_backpressure queue=websocket_messages`

`websocket_messages` identifies the per-WebSocket message queue; `stream_events` identifies the shared helper reader's per-request event queue. Helper lifecycle phases, liveness timeout, protocol, and transport identify distinct failure classes. Unknown helper phases are not echoed. The request ID identifies the connection-opening request, not necessarily the latest turn on a reused connection. Correlate timestamps with existing loop-lag and frame-size logs; no new success-path or payload logging is introduced. Public errors and account-health handling remain unchanged.
