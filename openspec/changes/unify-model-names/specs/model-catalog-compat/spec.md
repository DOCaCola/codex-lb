## ADDED Requirements

### Requirement: Operators name models in the model catalogue

Operator model names MUST be stored one row per slug in `model_display_names`. A name MUST replace the provider's
display name in the Codex catalog, `/v1/models`, the Anthropic models list, the dashboard model list and the settings
pickers, resolved once per build from a snapshot invalidated across replicas on every write. Routing, upstream request
bodies and the identity sent to a routed source model MUST keep the provider's name.

#### Scenario: Renaming an OpenRouter model
- **GIVEN** `openrouter/z-ai/glm-5.3-flash` is enabled
- **WHEN** `PUT /api/settings/model-display-names/openrouter/z-ai/glm-5.3-flash` stores "GLM Flash"
- **THEN** the next Codex and `/v1` model lists on every replica show "GLM Flash"
- **AND** requests for the model still reach OpenRouter as `z-ai/glm-5.3-flash`

#### Scenario: Removing a name
- **WHEN** the name for a renamed slug is deleted
- **THEN** the lists show the provider's name again

### Requirement: Model names are not stored per account

Provider account selections and model-source models MUST NOT carry display names. The upgrade MUST move existing
OpenRouter, OpenAI API and model-source names into `model_display_names`, keeping the first account's name when
accounts disagree, and remove them from the stored selections.

#### Scenario: Existing account names are migrated
- **GIVEN** an OpenRouter selection stored with a display name before the upgrade
- **WHEN** the migration runs
- **THEN** the name is stored for `openrouter/<model>` and removed from the stored selection

### Requirement: Operators manage model names through the settings API

`PUT /api/settings/model-display-names/{slug}` with `{"display_name": "..."}` (trimmed, 1–255 characters) MUST
create or replace the name of a catalogue model or redirect source. `DELETE` MUST remove it. Writes MUST require
dashboard write access and be audited as `settings_changed` naming `model_display_names`.

#### Scenario: Unknown slug
- **WHEN** a name is stored for a slug that is neither in the catalogue nor a redirect source
- **THEN** the response is 400 with code `model_not_in_catalogue`

#### Scenario: Deleting an absent name
- **WHEN** `DELETE` is called for a slug without a name
- **THEN** the response is 404 with code `model_display_name_not_found`

### Requirement: Per-model context window overrides resolve dashboard rows over the environment

Per-model reported context window overrides MUST be stored one row per slug in `model_context_window_overrides` and
resolved per slug as environment entry < dashboard row; a slug with neither reports the upstream window. The migration
and first boot MUST NOT copy the environment dict into rows. A stored or deleted row MUST take effect on the next
catalog request on every replica. The `CODEX_LB_MODEL_CONTEXT_WINDOW_OVERRIDES` variable remains as a deprecated
per-slug fallback for one release.

#### Scenario: Dashboard row overrides the environment entry for its slug

- **GIVEN** the process environment sets `CODEX_LB_MODEL_CONTEXT_WINDOW_OVERRIDES={"gpt-5.4": 300000}` and the upstream catalog reports `gpt-5.4` with `context_window=272000`
- **WHEN** `PUT /api/settings/model-context-window-overrides/gpt-5.4` stores `{"context_window": 515000}`
- **THEN** the next `GET /backend-api/codex/models` reports `gpt-5.4` with `context_window=515000` without a restart
- **AND** `GET /api/settings/model-context-window-overrides` lists `gpt-5.4` with `context_window=515000`, `source="dashboard"` and `env_value=300000`

#### Scenario: Deleted row returns the slug to the environment entry

- **GIVEN** a dashboard row `gpt-5.4 -> 515000` while the environment entry for `gpt-5.4` is `300000`
- **WHEN** `DELETE /api/settings/model-context-window-overrides/gpt-5.4` succeeds
- **THEN** the next catalog request reports `gpt-5.4` with `context_window=300000`
- **AND** the settings API lists `gpt-5.4` with `source="env"` and `env_value=300000`

### Requirement: Settings API lists the model catalogue and overrides

`GET /api/settings/model-context-window-overrides` MUST list the enabled text and image models offered to clients
(`models`: `slug`, `display_name`, `provider_display_name`, `renamed`, `image`, `provider`, `default_context_window` and
`max_context_window`, both windows `null` for image models) and the merged `overrides` (`slug`, effective
`context_window`, `source` `"dashboard"` or `"env"`, and `env_value`).

#### Scenario: Catalogue lists enabled models only

- **WHEN** a source model is disabled
- **THEN** `GET /api/settings/model-context-window-overrides` omits it from `models`
- **AND** `PUT` for its slug returns 400 with code `model_not_in_catalogue`

#### Scenario: Image models are listed without a window

- **GIVEN** an enabled OpenAI API image model `openai-apikey/gpt-image-2.6-sunburst`
- **WHEN** `GET /api/settings/model-context-window-overrides` is called
- **THEN** it is listed with `image=true` and `null` default and maximum windows
- **AND** `PUT` of a context window for it returns 400 with code `model_has_no_context_window`

### Requirement: Context window override writes are validated

`PUT /api/settings/model-context-window-overrides/{slug}` MUST upsert the row for a catalogue text model, so concurrent
creates both succeed; `DELETE` MUST remove it, returning 404 when no row exists. Writes MUST reject windows above the
model's ceiling, non-integer windows outside 1–2147483647 without coercion, and invalid slugs without trimming; the
slug segment MUST accept `/`. Each write MUST be audited as `settings_changed` naming
`model_context_window_overrides`.

#### Scenario: Slug known only to the environment has no row to delete

- **GIVEN** the environment entry `gpt-5.4 -> 300000` and no dashboard row for `gpt-5.4`
- **WHEN** `DELETE /api/settings/model-context-window-overrides/gpt-5.4` is called
- **THEN** the response is 404 with code `model_context_window_override_not_found`
- **AND** the environment entry keeps applying

#### Scenario: Dashboard value is clamped like an environment value

- **GIVEN** the upstream catalog reports a model with `context_window=272000` and `max_context_window=872000`
- **WHEN** the environment entry for that slug is `1000000`
- **THEN** `GET /v1/models` and `GET /backend-api/codex/models` report `872000` for every context budget field of that model
- **WHEN** `PUT /api/settings/model-context-window-overrides/{slug}` sends `{"context_window": 1000000}` for that model
- **THEN** the response is 400 with code `context_window_above_maximum` and no row is written

#### Scenario: Invalid window or slug is rejected

- **WHEN** `PUT /api/settings/model-context-window-overrides/gpt-5.4` sends `{"context_window": 0}`, `-1`, `1.5`, `515000.0`, `"515000"`, `true` or `2147483648`
- **THEN** the response is 422 and no row is written
- **WHEN** the slug segment is empty, longer than 256 characters, or contains whitespace (including leading or trailing whitespace) or a control character
- **THEN** the response is 400 with code `invalid_model_slug` and no row is written

### Requirement: Catalog builds resolve overrides from a cached snapshot

`GET /v1/models` and `GET /backend-api/codex/models` MUST resolve the merged overrides once per build from a cached row
snapshot that every write invalidates through the cross-replica `settings` namespace, without being overwritten by an
in-flight load. They MUST NOT read the database per entry, MUST clamp environment values to the ceiling, and MUST keep
serving the last known rows when the database is unreachable.

#### Scenario: Catalog build reads one cached snapshot

- **WHEN** `GET /v1/models` or `GET /backend-api/codex/models` builds its entries
- **THEN** the merged overrides are resolved once before the per-model loop from the cached row snapshot and the process settings
- **AND** no database read happens per model entry

## REMOVED Requirements

### Requirement: Per-model context window overrides are dashboard settings

**Reason**: The model catalogue now lists enabled image models and reports provider names, so the scenario "Catalogue
lists only enabled text models" no longer holds. The requirement is re-added above as four requirements (dashboard
rows over the environment, catalogue listing, write validation, cached snapshot) with that scenario replaced.

**Migration**: None; image models cannot take a context window override.
