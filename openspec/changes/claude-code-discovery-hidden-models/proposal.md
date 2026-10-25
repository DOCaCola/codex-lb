# Hide Catalog-Hidden Models From Claude Code Discovery

## Why

The Anthropic models list is Claude Code's `/model` picker, but it lists every Messages-servable model, including
models the catalog marks `visibility: hide` such as `codex-auto-review`. Claude Code keeps only `id`,
`display_name` and `description` from discovery, so it cannot hide them itself. Codex's own picker already omits
these models.

Of the references, only opencodex keeps internal models out of Claude Code discovery, through a fixed list of
chat models. CLIProxyAPI, OmniRoute and agent-lb list them. The catalog's visibility field carries the same
decision without a list that must be maintained by hand.

## What Changes

- The Anthropic models list omits models whose catalog visibility is not `list`.
- Hidden models stay routable when requested by name; aliases still decode.
- The OpenAI-shaped `/v1/models` list and the Codex catalog are unchanged.

## Impact

- Specs: `model-catalog-compat` (Anthropic models list).
- Code: Anthropic models list builder in `app/modules/proxy/api.py`.
