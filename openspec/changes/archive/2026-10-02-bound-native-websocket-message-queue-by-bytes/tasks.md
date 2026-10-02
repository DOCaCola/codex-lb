# Tasks

## 1. Queue bound

- [x] 1.1 Generalize the byte-budgeted queue over item type and size function. Keep stream-event sizing unchanged.
- [x] 1.2 Size native WebSocket messages by text bytes (doubled when a decoded Responses payload is retained), binary length, and close-reason bytes. Bound the message queue by 32 MiB and 4096 messages, and remove the 64-message cap.

## 2. Classification

- [x] 2.1 Map native `consumer_backpressure` to `local_websocket_backpressure` and include it in the account-neutral WebSocket error codes.
- [x] 2.2 Surface a relay-local disconnect message for that code on the direct WebSocket and HTTP bridge owners.

## 3. Tests

- [x] 3.1 A burst of 2000 Responses WebSocket messages drains intact while the consumer reads late.
- [x] 3.2 Send acknowledgements resolve while undelivered messages are queued.
- [x] 3.3 A stalled consumer fails at the byte budget with `consumer_backpressure` and the account-neutral code.

## 4. Verification

- [x] 4.1 Run Ruff, ty, and the focused pytest suites.
- [x] 4.2 Run strict OpenSpec validation for this change and the specs.
