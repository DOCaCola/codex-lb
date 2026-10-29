## Implementation

- [x] Confirm the production failure path, the client's recovery, and how the references report it.
- [x] Share the quota-caused owner-loss evidence between compact and the Responses paths.
- [x] Report the spent owner and its reset at WebSocket connect, at dispatch refusal, and on direct HTTP streams.
- [x] Keep the generic failure for proxy-injected anchors, file pins, turn-state owners and non-quota losses.
- [x] Add unit and integration regressions; run lint, types and the affected suites.
- [ ] Observe a quota-exhausted owner in production after deployment.
