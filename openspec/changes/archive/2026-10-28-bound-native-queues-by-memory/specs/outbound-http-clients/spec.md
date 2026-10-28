## MODIFIED Requirements

### Requirement: Native helper stream events are bounded per request by a byte budget

Events the native egress helper emits for one request MUST be buffered between the shared helper reader and that request's consumer in a per-request queue bounded by a 32 MiB memory budget. The queue MUST NOT cap the number of events. Each payload-bearing event MUST be charged its payload bytes plus a fixed 1 KiB per-item overhead. A payload-free control or terminal event MUST always be accepted and MUST NOT be charged. Queued bytes MUST be released as the consumer drains. A burst of small framed events, including one with more than 4096 events, or a body made of large chunks that fits the budget MUST NOT fail a consumer that is still draining. Only when a request's queue exceeds its budget MAY the reader fail that request with `consumer_backpressure`, drop its queued events, cancel the helper-side request, and continue serving other requests.

#### Scenario: Burst of small framed events drains without failure

- **GIVEN** the helper has 2000 small body events for one request buffered in its output pipe
- **WHEN** the consumer starts reading after the burst landed
- **THEN** the consumer receives the complete body and the request is not failed

#### Scenario: Tiny events are bounded through their per-item overhead

- **GIVEN** a request queue whose budget equals three charged one-byte events
- **WHEN** a fourth one-byte event arrives before the consumer drains
- **THEN** the event is rejected
- **AND** payload-free terminal events are still accepted

#### Scenario: A consumer that stops draining is bounded by bytes

- **GIVEN** a request whose consumer does not read while the helper emits 48 chunks of 1 MiB
- **WHEN** the queued payload exceeds 32 MiB
- **THEN** that request fails with `consumer_backpressure`
- **AND** other requests on the same helper keep being served

### Requirement: Native WebSocket messages are bounded per connection by a byte budget

Messages that a native upstream WebSocket's pump forwards to its consumer MUST be buffered in a per-connection queue bounded by a 32 MiB memory budget. The queue MUST NOT cap the number of messages. A message's payload size MUST count its UTF-8 text bytes, counted twice when a decoded Responses payload is retained alongside the text, plus binary data bytes and close-reason bytes. A message with a non-zero payload size MUST be charged that size plus a fixed 1 KiB per-item overhead. Queued bytes MUST be released as the consumer drains. A message arriving at an empty queue and a zero-byte message MUST be accepted. The pump MUST NOT block on this queue, so send acknowledgements keep resolving while messages wait for the consumer. A burst that fits the budget, including one with more than 4096 messages, MUST NOT fail a consumer that is still draining. Only when the budget is exceeded MAY the WebSocket fail with `consumer_backpressure` for the `websocket_messages` queue.

#### Scenario: Burst of Responses messages drains without failure

- **GIVEN** 8000 small Responses WebSocket messages arrive before the consumer reads
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
