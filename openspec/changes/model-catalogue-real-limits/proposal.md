## Why

Context limits for Claude and OpenRouter models were set in three places: a
hard-coded 272k Claude client default with its own compaction hint, a 262144
OpenRouter default with per-account context and output caps, and the global
per-model override list. Operators could not see a model's real capacity or
which value applied, and the Claude compaction hint diverged from how the
Codex client derives compaction for OpenAI's own catalog (90% of the reported
window, no explicit threshold).

## What Changes

- Source models (Claude, OpenRouter, OpenAI-compatible) advertise their real
  capacity as both `context_window` and `max_context_window`. No source
  model advertises `auto_compact_token_limit`; the client derives it.
- OpenRouter context and output limits follow the provider catalog
  (`top_provider` limits when stricter); per-account context/output caps are
  removed and a migration strips stored caps and forces a re-projection.
- The Claude 272k client default and its compaction hint are removed.
- Settings → Model catalogue becomes the single override surface: it lists the
  enabled text models with their default and maximum window, and an override
  is accepted only for a listed model and only up to its maximum.
- Codex-native models keep upstream values unless explicitly overridden.

## Capabilities

### Modified Capabilities

- `model-catalog-compat`: source-model ceilings, catalogue listing and
  override validation.
- `claude-accounts`: Claude client context follows discovered capacity.
- `openrouter-accounts`: limits follow the provider catalog; no caps.

## Impact

- Backend: model-source catalog projection, OpenRouter catalog/schemas, proxy
  context resolution, settings API and schemas, one migration.
- Frontend: model catalogue settings table, OpenRouter model picker, Claude
  model selection.
- Deployment: operators who want a smaller Claude window set it in the model
  catalogue (production: 350000 for active Claude models).
