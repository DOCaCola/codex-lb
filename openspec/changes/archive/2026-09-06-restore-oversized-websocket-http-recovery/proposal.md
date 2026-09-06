# Change: Restore oversized WebSocket request recovery

## Why

Codex resends a Responses request over HTTPS after its WebSocket stream retry
budget is exhausted. codex-lb currently maps an oversized client WebSocket
`response.create` to status `400`, which Codex treats as a terminal invalid
request, so a payload that the upstream HTTP endpoint could accept never reaches
that endpoint.

## What Changes

- Emit status `413` for an oversized `response.create` received over the
  client-facing Responses WebSocket after historical slimming cannot make it
  fit the upstream WebSocket budget.
- Preserve status `400` for the equivalent guard on HTTP requests and other
  upstream-WebSocket callers that do not have the Codex WebSocket fallback
  contract.
- Preserve the existing error envelope, pre-upstream rejection, dump, and
  reservation cleanup behavior.

## Impact

- Affected spec: `responses-api-compat`
- Affected code: the service-level `response.create` size guard and WebSocket
  compatibility tests
