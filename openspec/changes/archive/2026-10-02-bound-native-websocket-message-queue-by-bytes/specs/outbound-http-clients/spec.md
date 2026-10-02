# outbound-http-clients Delta

## ADDED Requirements

### Requirement: Native WebSocket messages are bounded per connection by a byte budget

Messages that a native upstream WebSocket's pump forwards to its consumer MUST be buffered in a per-connection queue. That queue is bounded by a queued-payload byte budget (32 MiB) together with a message-count cap (4096). A message's size MUST count its UTF-8 text bytes, counted twice when a decoded Responses payload is retained alongside the text, plus binary data bytes and close-reason bytes. Queued bytes MUST be released as the consumer drains. A message arriving at an empty queue and a zero-byte message, while the count cap has room, MUST be accepted. The pump MUST NOT block on this queue, so send acknowledgements keep resolving while messages wait for the consumer. A burst that fits the budget MUST NOT fail a consumer that is still draining. Only when the budget is exceeded MAY the WebSocket fail with `consumer_backpressure` for the `websocket_messages` queue.

#### Scenario: Burst of Responses messages drains without failure

- **GIVEN** 2000 small Responses WebSocket messages arrive before the consumer reads
- **WHEN** the consumer then drains the WebSocket
- **THEN** it receives every message in order and the WebSocket is not failed

#### Scenario: Send acknowledgements are not held behind queued messages

- **GIVEN** undelivered messages are queued for a native WebSocket
- **WHEN** the consumer sends a frame and the helper acknowledges it
- **THEN** the send completes without the consumer receiving the queued messages

#### Scenario: A consumer that stops draining is bounded by bytes

- **GIVEN** a native WebSocket whose consumer does not read
- **WHEN** its queued message payload exceeds 32 MiB
- **THEN** the WebSocket fails with `consumer_backpressure` for `websocket_messages`
