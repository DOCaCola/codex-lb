# Tasks

## 1. Implementation

- [x] 1.1 Add the process-wide idle WebSocket reclaimer and use it in the bulkhead WebSocket lane.
- [x] 1.2 Track owed client tool results and reclaim requests on the downstream activity; register client Responses
  sockets; replace the timed idle close with the reclaim close.
- [x] 1.3 Remove `proxy_downstream_websocket_idle_timeout_seconds` from settings, dashboard overrides, tiers, the
  settings API, the database (migration) and the dashboard, and update documentation.

## 2. Verification

- [x] 2.1 Reclaimer and bulkhead tests: LRU selection, protected sockets, admission after release, 429 without a
  candidate or after the wait.
- [x] 2.2 WebSocket route tests: quiet socket stays open, reclaim closes an idle socket, a pending request and owed
  tool results block reclaim.
- [x] 2.3 Settings API, migration and dashboard tests updated.

