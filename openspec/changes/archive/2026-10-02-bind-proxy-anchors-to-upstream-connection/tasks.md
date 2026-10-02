# Tasks

## 1. Connection identity

- [x] 1.1 Assign an identity to every upstream WebSocket connection and HTTP bridge session connection; a reconnect assigns a new one.
- [x] 1.2 Record the completing connection on proxy-injected anchors; replace `last_completed_response_account_id`.

## 2. WebSocket

- [x] 2.1 Select a continuity anchor only on the connection that completed it.
- [x] 2.2 At the send boundary, withdraw an anchor from another connection and install the verified unanchored replay; otherwise fail closed locally.

## 3. HTTP bridge

- [x] 3.1 Withdraw a retired-connection anchor before send.
- [x] 3.2 Send full resends on a fresh connection unanchored; fail delta-only requests closed before session creation.
- [x] 3.3 Remove durable anchor hydration and the pre-session durable bind; clear completed-response state on reconnect.
- [x] 3.4 Owner-forward recovery injects only an anchor the local session completed.

## 4. Tests

- [x] 4.1 Same-connection anchoring still trims; a replacement connection receives the full replay; a delta without replay fails closed.
- [x] 4.2 HTTP bridge fresh reattach: full resend unanchored, delta fail-closed, retired anchor withdrawn at send.
- [x] 4.3 Owner retirement, quarantine and Responses Lite classification tests reflect connection-scoped anchors.
