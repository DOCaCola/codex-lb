## Backend

- [x] Add the `model_redirects` table, model and migration (single Alembic head), and the nullable
  `request_logs.requested_model` column.
- [x] Add the repository and a `DashboardRowsCache` snapshot invalidated through the `settings` namespace.
- [x] Add the single model resolver (suffix alias, key enforcement, redirect) and replace
  `effective_model_for_api_key` and every inline `enforced_model` resolution; make the Claude and
  Antigravity routing guards use the resolution.
- [x] Apply the resolver on every covered Responses, chat-completions and Messages surface, before
  model-source selection; fail with `model_redirect_target_unavailable` for inactive redirects.
- [x] Check `allowed_models` against the requested model; keep limits and accounting on the served model.
- [x] Render redirect sources from the target in the Codex, `/v1/models` and Anthropic catalog builders;
  ignore source context-window overrides while redirected.
- [x] Add `GET/PUT/DELETE /api/settings/model-redirects` with validation, default hiding, audit events and
  cache invalidation; reject conflicting compaction routes in both APIs.
- [x] Write `requested_model` in request logs; return it and match it in the model filter.
- [x] Tests: resolution order on each surface, cross-provider target, enforced-model redirect, compaction
  route on the served model, inactive target, no `OpenAI-Model` header, allowlists, catalogs, settings API,
  request logs.

## Frontend

- [x] HTML mockup of the Redirects card and catalogue markers for review before implementation.
- [x] Redirects card, catalogue row markers, disabled source overrides, compaction-picker exclusion and the
  `requested -> served` log cell.
- [x] Hooks, schemas, locales, MSW handlers and handler coverage; component tests.

## Wrap-up

- [x] Run backend and frontend checks and `openspec validate redirect-requested-models --strict`.
- [x] Verify end to end against the local mock setup (Codex app-server, Claude Code, `/v1` client).
