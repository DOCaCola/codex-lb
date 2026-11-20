# Redirect requested models

## Why

Operators want a model name that clients request to be served by another model: a retired model
(`gpt-5.4`) answered by its successor (`gpt-5.5`), or a model kept in old configurations and
conversations moved to a cheaper or newer one, without editing every client. codex-lb has no such
control. The closest tools are blunt: an API key's `enforced_model` forces every request of that key
onto one model, compaction routes rewrite only compaction requests, and the built-in suffix aliases
(`gpt-5.5-high-fast`) are fixed.

Five of the seven references ship this: CLIProxyAPI (`oauth-model-alias`, per provider and per
credential, with `fork`, `display-name` and `force-mapping`), agent-lb (`model_aliases`, logs the
requested alias and answers `x-agent-lb-model-rewritten`), sub2api (per-account `model_mapping`, plus
`compact_model_mapping`), OmniRoute (exact and wildcard aliases, combos) and opencodex (provider
`modelAliases`, combos). They agree on the core: rewrite early, before routing, and keep both names
in the logs.

## What Changes

- New dashboard-managed redirects, one row per requested model in `model_redirects`
  (`source_model` -> `target_model`), edited in Settings > Models > Model catalogue.
- One model resolution replaces the scattered `effective_model_for_api_key` copies: suffix-alias
  normalization, then API-key model enforcement, then the redirect. Model-source selection, Claude,
  Antigravity and OpenRouter routing, account selection, compaction routes, effort policy, pricing and
  request logs all use the resolved model.
- Redirects apply to text-generation requests on every client surface: Codex Responses (HTTP,
  WebSocket, owner-forwarded, non-streaming, `/responses/compact`, prewarm), `/v1/responses`,
  `/v1/chat/completions` and Anthropic `/v1/messages`.
- Client catalogs serve the requested slug with the served model's metadata (context window, effort
  levels, input modalities, instructions, capabilities), so clients build requests for the model that
  answers them. Its visibility follows the existing hide switch.
- API-key `allowed_models` authorizes the requested model (after key enforcement), not the served one.
- Request logs keep the served model in `model` (pricing unchanged) and add `requested_model`, set
  only when a redirect applied. Logs show `requested -> served`.
- `GET/PUT/DELETE /api/settings/model-redirects` with validation and audit events.

## Capabilities

### Modified Capabilities

- `model-catalog-compat`: redirect storage, resolution order, surfaces and catalog rendering.
- `api-keys`: model restrictions apply to the requested model of a redirect.
- `provider-request-log-attribution`: requested model of a redirected request.
- `frontend-architecture`: redirects card and catalogue markers.

## Impact

- Backend: new table and migration, settings repository and API, a cached snapshot, one model
  resolver replacing `effective_model_for_api_key` and its copies in `app/modules/proxy/api.py`,
  `service.py`, `_service/codex_control.py`, `model_sources/selection.py`, `claude/routing.py` and
  `antigravity/routing.py`; the three catalog builders; request-log writer and schema.
- Frontend: Model catalogue card, catalogue row markers, request-log model cell, hooks, schemas,
  locales, MSW handlers.
- Clients: adding or removing a redirect changes the Codex catalog and the served model, so each open
  conversation on the redirected model loses its prompt cache once, as with a model switch.
