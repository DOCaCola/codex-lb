# Hide models from client model lists

## Why

Operators want to retire older models from client pickers without breaking the
conversations, configurations and compaction routes that still name them. Today
the only control that removes a model from a list also removes access: API-key
`allowed_models` restricts usage, and deselecting a source model or disabling its
source makes the slug unroutable. When a Codex thread's model disappears from the
catalog entirely, the client falls back to generic metadata (272k window, generic
instructions, no reasoning levels, 10 KB tool-output truncation) and the request
then fails at codex-lb or upstream.

The Codex client already separates listing from availability: a catalog entry
with `visibility: "hide"` keeps its full metadata for threads, `config.toml` and
subagents that name it, and is only left out of the pickers. codex-lb needs an
operator control that uses this.

## What Changes

- New per-model "Client lists" switch in Settings › Models › Model catalogue,
  stored as one row per hidden slug in a new `hidden_models` table.
- A hidden model is served in the Codex catalog with `visibility: "hide"` and
  its full metadata, and is omitted from the OpenAI-shaped `/v1/models` list and
  the Claude Code model list.
- Routing, API-key allowed models, account model selection, compaction routes,
  pricing, context-window overrides and the routed base instructions are
  unchanged.
- `GET /api/settings/model-context-window-overrides` reports `listed` for each
  catalogue model; `PUT`/`DELETE /api/settings/hidden-models/{slug}` hide and
  list a model.

## Impact

- Backend: settings API and repository, a migration, a cached snapshot read by the
  catalog builders in `app/modules/proxy/api.py`.
- Frontend: Model catalogue table, settings hooks and schemas, locales, MSW handlers.
- Clients: changing the listed set changes the Codex client's model text and its
  `spawn_agent` description, so each open conversation loses its prompt cache once.

