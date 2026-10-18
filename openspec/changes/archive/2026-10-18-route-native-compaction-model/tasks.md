# Tasks

- [x] Add the `model_compaction_routes` table, migration and repository.
- [x] Add the route compatibility rules and a cached snapshot invalidated through the `settings` namespace.
- [x] Apply active routes in API-key enforcement for native compaction requests on HTTP, WebSocket, owner-forwarded,
  non-streaming and `/responses/compact` paths.
- [x] Add `GET/PUT/DELETE /api/settings/model-compaction-routes` with audit events.
- [x] Add the Compaction routing card to Settings -> Model catalogue.
- [x] Cover the rules, the rewrite on each surface and the settings API with tests.
- [x] Verify end to end on production (WebSocket and HTTP Codex clients, `/responses/compact`).
