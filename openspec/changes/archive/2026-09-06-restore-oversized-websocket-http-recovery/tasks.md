## 1. Specification

- [x] 1.1 Define transport-scoped oversized `response.create` status behavior.

## 2. Implementation

- [x] 2.1 Return `413` from the service guard for client WebSocket request states.
- [x] 2.2 Retain `400` for HTTP request states and low-level upstream WebSocket callers.

## 3. Verification

- [x] 3.1 Cover the externally visible WebSocket error event and pre-connect behavior.
- [x] 3.2 Cover service guard behavior for WebSocket and HTTP request states.
- [x] 3.3 Run focused tests, lint, formatting, and strict OpenSpec validation.
