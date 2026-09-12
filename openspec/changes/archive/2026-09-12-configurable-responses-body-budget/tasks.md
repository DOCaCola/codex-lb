## Tasks

- [x] Implement validated shared budget across HTTP, compact, default WebSocket, internal owner forwarding, and replay.
- [x] Add local refusal diagnostics without changing unrelated route contracts.
- [x] Add configuration, route, compression, replay, and listener regression coverage.
- [x] Update normative specs and operator documentation.
- [x] Run focused tests, lint, typing, and strict spec validation.

## Verification

- Ingress/configuration/CLI/settings suites: 197 passed.
- Full bridge and proxy utility suites: 2672 passed.
- Image route and native transport suites: 104 passed.
- `make lint`, `ty check`, strict change validation, and 65 main specs: passed.
- No production requests, configuration edits, deployment, commit, or push.
