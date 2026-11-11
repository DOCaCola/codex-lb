## Backend

- [x] Add the `hidden_models` table, model and migration (single Alembic head).
- [x] Add the repository and a `DashboardRowsCache` snapshot invalidated through the `settings` namespace.
- [x] Add `PUT`/`DELETE /api/settings/hidden-models/{slug}` with validation, audit events and cache invalidation.
- [x] Report `listed` for each model in `GET /api/settings/model-context-window-overrides`.
- [x] Apply hiding in the Codex catalog, OpenAI-shaped `/v1/models` and Anthropic list builders.
- [x] Cover catalogs, per-key allowlists, routing, routed instructions, metadata ownership and the API in tests.

## Frontend

- [x] Add the "Client lists" switch column, provider grouping, filter and note to the model catalogue.
- [x] Mark hidden models in the compaction route pickers.
- [x] Update hooks, schemas, locales, MSW handlers and handler coverage; add component tests.

## Wrap-up

- [x] Run backend and frontend checks and `openspec validate hide-models-from-client-lists --strict`.
- [ ] Archive.

