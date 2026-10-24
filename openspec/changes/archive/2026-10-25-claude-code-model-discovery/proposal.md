# Claude Code Model Discovery

## Why

Claude Code can now use OpenAI accounts and Responses model sources through `/v1/messages`. Its `/model` picker,
however, shows none of them. Claude Code 2.1.283 discovers gateway models only when
`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY` is set. It calls `GET /v1/models?limit=1000` with an
`anthropic-version` header, keeps only `id`, `display_name` and `description`, and discards every entry whose ID
does not contain `claude` or `anthropic`. Users therefore have to type model names or maintain a `modelPicker`
list by hand.

opencodex solves this on the server. It lists routed models under reversible `ocx-claude-…` aliases whose display
names state the real model, and decodes them on `/v1/messages`.

## What Changes

- `GET /v1/models` with an `anthropic-version` header and no `client_version` returns an Anthropic models list.
  Codex catalog and OpenAI list responses are unchanged.
- The list contains the models `/v1/messages` can serve for the API key:
  - native OpenAI models and Responses-capable source models under a `clb-claude-` alias;
  - Claude models under their Anthropic ID.
  Display names and descriptions name the real model and its provider. Order: OpenAI, Claude, then other models.
- `/v1/messages` and `/v1/messages/count_tokens` decode the alias before applying the API key's enforced model and
  routing. Logs, limits and pricing use the decoded model. Responses echo the model spelling the client sent.
- Client documentation enables discovery and explains context-window settings for routed models.

## Non-goals

- `[1m]` picker variants. Catalogue windows are capped below 1M; `CLAUDE_CODE_MAX_CONTEXT_TOKENS` covers the rest.
- Writing Claude Code's model cache. opencodex does this because its launcher sets no token. codex-lb clients
  authenticate with an API key, so Claude Code refreshes the cache itself.
- Claude Desktop third-party model configuration.

## Impact

- Specs: `model-catalog-compat` (Anthropic models list), `messages-api-compat` (alias decoding).
- Code: `/v1/models` handler, a small alias module under `app/core/messages/`, `claude_messages` routing.
- Docs: Claude Code section of `docs/client-setup.md`.
