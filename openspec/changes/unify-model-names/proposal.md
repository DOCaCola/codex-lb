## Why

Model names could only be changed per provider account: OpenRouter and OpenAI API selections carried a display name,
generic model sources had a per-model name field, and Claude, Antigravity and Codex-native models could not be renamed
at all. Image models were missing from the model catalogue, so they could be neither renamed nor inspected there.

## What Changes

- New `model_display_names` table (`slug -> display_name`) with `PUT`/`DELETE /api/settings/model-display-names/{slug}`.
  A name replaces the provider's name in the Codex catalog, `/v1/models`, the Anthropic models list, the dashboard
  model list and the settings pickers. Routing and the identity sentence sent to routed models keep the provider name.
- The model catalogue lists enabled image models (without a context window) and reports each entry's provider name and
  whether it is renamed.
- Settings > Models > Model catalogue gets search, a provider filter and an inline editor for name and context window.
- **BREAKING**: OpenRouter and OpenAI API selections and model-source models no longer accept a display name. A
  migration moves existing names into the new table (first account wins on conflicting slugs) and strips them from
  stored selections.

## Capabilities

### Modified Capabilities
- `model-catalog-compat`: operator model names; the catalogue includes image models.
- `frontend-architecture`: the model catalogue edits names and windows inline and adds search and a provider filter.
- `openrouter-accounts`: selections no longer carry display names.
- `model-source-routing`: source models no longer carry an editable display name.

## Impact

`app/modules/settings`, the `app/modules/proxy/api.py` catalog builders, `app/modules/dashboard/api.py`, the OpenRouter,
OpenAI API and model-source schemas, a new migration, and the dashboard catalogue, pickers and model-source editor.
