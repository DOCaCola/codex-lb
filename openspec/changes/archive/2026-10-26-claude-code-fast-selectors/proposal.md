# Claude Code Fast selectors for OpenAI models

## Why

Claude Code turns its `/fast` toggle into `speed: "fast"` only on the first-party Anthropic API, for models it knows
support fast mode (Opus), after an organization check against Anthropic itself. Gateway discovery keeps only a
model's ID, name and description, so codex-lb cannot advertise Fast for the OpenAI models it lists. A Claude Code
client therefore has no way to request the priority tier for an OpenAI model, although codex-lb already maps
`speed: "fast"` to it.

opencodex solves the same gap by publishing a selectable `--fast` sibling for every Fast-capable model
(feat `fast-row`, enabled by default since 2026-09-06).

## What Changes

- Claude Code discovery lists a `… · Fast` sibling, `clb-claude-<model>~fast`, after each listed OpenAI account model
  whose catalog offers the priority tier. The terminal `~fast` marker cannot occur in an escaped model name.
- Fast rows are omitted when Fast Mode is prohibited or the API key enforces a service tier.
- A Messages request for a Fast selector is served as the base model with `service_tier: "priority"`. A Fast
  selector for a model without the priority tier is rejected before dispatch.

## Impact

- Claude Code users choose Fast for an OpenAI model from `/model`; logging, limits and pricing follow the priority
  tier as for `/v1/responses`.
- Claude Code's own `/fast` toggle and Claude account fast mode are unchanged.
