## 1. Accounts, identity and metadata

- [x] 1.1 Add Antigravity tables and a single-head migration (accounts, OAuth flows, version state, quota history, cooldowns).
- [x] 1.2 Implement the version service: manifest check, verified archive changelist extraction, seeded record, pin, per-request snapshot.
- [x] 1.3 Implement Google OAuth (PKCE paste flow), credential import shapes, token refresh and userinfo.
- [x] 1.4 Implement the Cloud Code client: native headers, loadCodeAssist, onboardUser polling, fetchAvailableModels, retrieveUserQuotaSummary.
- [x] 1.5 Implement account lifecycle: create paused, reconnect by subject, update, refresh, delete; catalog effort families and model projection.
- [x] 1.6 Implement quota parsing, plan weights, history and the background scheduler.
- [x] 1.7 Add dashboard API endpoints with audit and redaction.

## 2. Inference

- [x] 2.1 Tool name codec and Gemini schema compiler.
- [x] 2.2 Responses → Gemini envelope translation, including history pairing, images, tool choice and signature replay.
- [x] 2.3 Gemini SSE → Responses projection with usage, finish reasons, custom tools and empty-completion guard.
- [x] 2.4 Error taxonomy, transport and bounded recovery loop; account state transitions for ban, verification and reauth.
- [x] 2.5 Routing: eligibility, family quota, stickiness, shared strategy.
- [x] 2.6 Wire into source dispatch (HTTP, SSE, WebSocket, Messages/Chat front-ends), request logs and throughput.
- [x] 2.7 Offer Codex `web_search` as the CLI's `search_web`: catalog search model, gateway-run grounded search on the dispatching account, multi-round responses and sealed replay.

## 3. Dashboard and verification

- [x] 3.1 Frontend: add-account group, account list/detail with per-family quota, catalog selection, version controls and dashboard provider toggle.
- [x] 3.2 Contract tests against the captured CLI 1.4.10 wire image and mock scenarios; lint, type checks, migration topology, frontend tests and build.
- [x] 3.3 Sync specs and record verification limits.
