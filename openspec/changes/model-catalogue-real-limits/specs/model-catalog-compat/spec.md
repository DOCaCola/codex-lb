## MODIFIED Requirements

### Requirement: OpenAI-compatible model metadata uses backend context windows

When serving `GET /v1/models`, the system SHALL expose `metadata.context_window` as the upstream backend `context_window` budget by default. The system MUST NOT promote raw `max_context_window` values or hard-coded full-context guesses into `metadata.context_window`. Explicit operator context-window overrides — a `model_context_window_overrides` dashboard row for the slug, else the `CODEX_LB_MODEL_CONTEXT_WINDOW_OVERRIDES` entry for the slug (see "Per-model context window overrides are dashboard settings") — remain the highest-priority reported-context value, clamped to the model's context-window ceiling (see "Source models advertise their real capacity").

#### Scenario: GPT-5 Codex models are reported with the backend context window on /v1/models

- **WHEN** the upstream model catalog contains `gpt-5.5`, `gpt-5.4-mini`, `gpt-5.3-codex`, or `gpt-5.4` with `context_window=272000`
- **THEN** `GET /v1/models` returns each entry with `metadata.context_window=272000`

#### Scenario: raw max_context_window does not inflate /v1/models context_window

- **WHEN** the upstream model catalog contains a model with `context_window=272000` and `max_context_window=900000`
- **THEN** `GET /v1/models` returns that entry with `metadata.context_window=272000`

### Requirement: OpenAI-compatible model metadata preserves the backend input budget explicitly

When serving `GET /v1/models`, the system SHALL expose the upstream backend input/context budget in `metadata.input_context_window`. When an explicit operator context-window override (dashboard row, else environment entry) applies to a model, that override SHALL be the reported input budget as well, clamped to the model's context-window ceiling (see "Source models advertise their real capacity"), so `metadata.input_context_window` and the OpenAI-compatible `context_length`, `contextLength`, and `capabilities.context_length` fields never contradict `metadata.context_window` and never advertise more input than the backend sanctions. For subscription models a `max_context_window` equal to the backend `context_window` — the parseability default synthesized for bootstrap entries — MUST NOT clamp an override, so raise overrides for those models keep working. For models whose reported `metadata.context_window` is not operator-overridden, `metadata.context_window` and `metadata.input_context_window` SHOULD be equal. The system SHOULD expose `metadata.max_output_tokens` for known GPT-5 Codex models when that output-budget value is known; that value MUST NOT be used to inflate `metadata.context_window`.

#### Scenario: /v1/models exposes the 272k backend input budget explicitly

- **WHEN** the upstream model catalog contains a known GPT-5 Codex model with `context_window=272000`
- **THEN** `GET /v1/models` returns that model with `metadata.input_context_window=272000`
- **AND** `metadata.context_window=272000`

#### Scenario: Explicit reported-context overrides do not hide the backend input budget

- **WHEN** an operator override sets a model's reported `metadata.context_window` to `515000`
- **AND** the upstream model catalog contains that model with `context_window=272000` and no `max_context_window`
- **THEN** `GET /v1/models` returns that model with `metadata.context_window=515000`
- **AND** `metadata.input_context_window=515000`
- **AND** `context_length`, `contextLength`, and `capabilities.context_length` of `515000`

#### Scenario: An override never advertises more input than the backend ceiling

- **WHEN** an operator override sets a model's reported context window to `1000000`
- **AND** the upstream model catalog contains that model with `context_window=272000` and `max_context_window=872000`
- **THEN** `GET /v1/models` returns that model with `metadata.context_window=872000`
- **AND** `metadata.input_context_window=872000`
- **AND** `context_length`, `contextLength`, and `capabilities.context_length` of `872000`

#### Scenario: A synthesized ceiling equal to the backend budget does not clamp an override

- **WHEN** an operator override sets a bootstrap subscription model's reported context window to `32768`
- **AND** that model declares `context_window=8192` and the bootstrap entry synthesizes `max_context_window=8192`
- **THEN** `GET /v1/models` returns that model with `metadata.context_window=32768`
- **AND** `metadata.input_context_window=32768`
- **AND** `context_length`, `contextLength`, and `capabilities.context_length` of `32768`

#### Scenario: /v1/models exposes max output budget for known GPT-5 Codex models

- **WHEN** `GET /v1/models` returns `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, or `gpt-5.3-codex`
- **THEN** the entry's metadata includes `max_output_tokens=128000`

#### Scenario: A source-model override is clamped to declared capacity

- **WHEN** an operator override sets a source model's reported context window to `2000000`
- **AND** that source model declares a capacity of `1000000`
- **THEN** `GET /v1/models` reports `metadata.context_window=1000000` and `metadata.input_context_window=1000000`

### Requirement: Codex-native model catalog keeps backend catalog fields

When serving `GET /backend-api/codex/models`, the system MUST keep Codex-native model catalog semantics unchanged: the top-level `context_window` field remains the backend compact/input budget unless an explicit operator override applies, and upstream raw fields such as `max_context_window` remain available when upstream provides them. The `/v1/models` compatibility metadata MUST NOT mutate the native Codex endpoint.

When an explicit operator context-window override (dashboard row, else environment entry) applies to a model, the native entry SHALL report the single resolved value — the override clamped to the model's context-window ceiling; for subscription models a `max_context_window` equal to the backend `context_window` (the synthesized parseability default) MUST NOT clamp — on `context_window`, and SHALL rewrite `max_context_window` to that same resolved value when upstream provides the field. The endpoint's OpenAI-compatible `data` alias SHALL report the same resolved value on its `context_length`, `contextLength`, `capabilities.context_length`, `metadata.context_window`, and `metadata.input_context_window` fields, so the native and alias views of one model never advertise different budgets.

#### Scenario: Native Codex route preserves compact budget

- **WHEN** the upstream model catalog contains `gpt-5.5` with `context_window=272000`
- **THEN** `GET /backend-api/codex/models` returns `gpt-5.5.context_window=272000`
- **AND** it does not replace that field with `400000`

#### Scenario: Codex model catalog also exposes OpenAI data alias

- **WHEN** a client requests `GET /backend-api/codex/models`
- **THEN** the response keeps the Codex-native `models` list
- **AND** the response includes `object: "list"` and an OpenAI-compatible `data` list
- **AND** `data` contains model entries whose Codex visibility is `list`
- **AND** `data` excludes entries whose Codex visibility is `hide`

#### Scenario: Native Codex catalog reports one resolved budget for a clamped override

- **WHEN** an operator override sets a model's reported context window to `1000000`
- **AND** the upstream model catalog contains that model with `context_window=272000` and `max_context_window=872000`
- **THEN** `GET /backend-api/codex/models` returns that model with `context_window=872000`
- **AND** `max_context_window=872000`

#### Scenario: Codex data alias reports the resolved input budget for an override

- **WHEN** an operator override sets a model's reported context window to `515000`
- **AND** the upstream model catalog contains that model with `context_window=272000` and no explicit `max_context_window`
- **THEN** the `GET /backend-api/codex/models` `data` alias entry for that model reports `context_length`, `contextLength`, and `capabilities.context_length` of `515000`
- **AND** `metadata.context_window=515000` and `metadata.input_context_window=515000`
- **AND** the native `models` entry reports `context_window=515000`

### Requirement: Source-model Codex catalog entries are Codex-parseable

Codex catalog entries built for OpenAI-compatible source models MUST be
parseable by Codex clients without relying on bundled metadata. The entry MUST
report the source model's capacity as both `context_window` and
`max_context_window`; when the source model has no configured context window,
that capacity is 128,000 tokens. The entry MUST NOT include
`auto_compact_token_limit`; Codex clients derive compaction from the reported
window as they do for OpenAI's own catalog. The
entry MUST include `shell_type` (`shell_command`), a `truncation_policy`,
and the client-capability fields `include_skills_usage_instructions`,
`supports_image_detail_original`, `supports_search_tool`,
`use_responses_lite`, and `experimental_supported_tools`, defaulting each to
its most conservative value. Operator-provided values for these keys in the
source model's `raw_metadata_json` MUST take precedence over the defaults.

#### Scenario: Source model without a context window gets the default budget

- **GIVEN** an enabled Responses-capable source model with no `contextWindow` configured
- **WHEN** a client calls `GET /backend-api/codex/models`
- **THEN** the model's entry reports `context_window` of 128000
- **AND** `max_context_window` of 128000
- **AND** `shell_type` of `shell_command`
- **AND** conservative defaults for the client-capability fields (for example `supports_search_tool` is `false` and `use_responses_lite` is `false`)

#### Scenario: Operator capability opt-in overrides the defaults

- **GIVEN** a source model whose `raw_metadata_json` sets `"supports_search_tool": true`
- **WHEN** a client calls `GET /backend-api/codex/models`
- **THEN** the model's entry reports `supports_search_tool` as `true`

### Requirement: Per-model context window overrides are dashboard settings

The per-model reported context window override (`model_context_window_overrides`, `slug -> window`) MUST be managed from the dashboard as one row per slug in the `model_context_window_overrides` table (`slug`, `context_window`), resolved per slug as environment entry < dashboard row: a slug with a row reports the row's window, a slug without a row inherits the `CODEX_LB_MODEL_CONTEXT_WINDOW_OVERRIDES` entry for that slug, and a slug with neither has no override (the catalog reports the upstream window). The migration and the first boot MUST NOT copy the environment dict into rows. The settings API MUST expose under `GET /api/settings/model-context-window-overrides` the catalogue of enabled text models offered to clients (`models`: each with `slug`, `display_name`, `provider`, `default_context_window` and `max_context_window`, the latter being the model's context-window ceiling or `null` when none is known) and the overrides (`overrides`) as the merged per-slug list, each entry carrying `slug`, the effective `context_window`, a `source` of `"dashboard"` or `"env"`, and `env_value` (the environment entry for the slug, `null` when none); `PUT /api/settings/model-context-window-overrides/{slug}` with `{"context_window": n}` MUST create or replace the row for `slug` in a single upsert, so concurrent creates of the same absent slug both succeed, and `DELETE /api/settings/model-context-window-overrides/{slug}` MUST remove it (404 when no row exists, including for a slug that only the environment knows). A write MUST reject with 400 `model_not_in_catalogue` a slug that is not in that catalogue and with 400 `context_window_above_maximum` a value above the model's ceiling. A write MUST reject a `context_window` that is not an integer between 1 and 2147483647 (the width of the stored column) — a float, a numeric string and a boolean are rejected, not coerced — and a slug that is empty, longer than 256 characters, or contains whitespace or non-printable characters; a slug MUST NOT be trimmed into validity, and the slug segment MUST accept `/`. The catalog endpoints (`GET /v1/models`, `GET /backend-api/codex/models`) MUST resolve the merged overrides once per catalog build from a cached snapshot of the rows that the settings API invalidates durably through the cross-replica `settings` cache namespace on every write — an invalidation MUST NOT be overwritten by a load that was already in flight when it happened —, MUST NOT read the database per model entry, and MUST apply the ceiling clamp to an environment value. Each store and delete MUST be recorded as a `settings_changed` audit event naming `model_context_window_overrides` and the slug. A stored or deleted row takes effect on the next catalog request on every replica without a restart; when the database is unreachable past the snapshot's TTL the catalog MUST keep serving the last known rows rather than failing the request. The environment variable remains as a deprecated per-slug fallback for one release and is removed in the next minor.

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

#### Scenario: Catalog build reads one cached snapshot

- **WHEN** `GET /v1/models` or `GET /backend-api/codex/models` builds its entries
- **THEN** the merged overrides are resolved once before the per-model loop from the cached row snapshot and the process settings
- **AND** no database read happens per model entry

#### Scenario: Catalogue lists only enabled text models

- **WHEN** a source model is disabled or an OpenRouter model only produces images
- **THEN** `GET /api/settings/model-context-window-overrides` omits it from `models`
- **AND** `PUT` for its slug returns 400 with code `model_not_in_catalogue`

## ADDED Requirements

### Requirement: Source models advertise their real capacity

Source models SHALL report their real capacity as the default context window and as the ceiling: Claude models the discovered or maintained input capacity, OpenRouter models the provider catalog `context_length` limited by `top_provider.context_length` when stricter, and OpenAI-compatible models their configured window. The catalog MUST NOT apply provider-specific default caps or advertise compaction thresholds for source models; the Settings model catalogue is the only place to lower a reported window. Codex-native subscription models keep their upstream `context_window` and `max_context_window` unless an override applies.

#### Scenario: Claude model at full capacity

- **WHEN** a Claude model's discovered input capacity is `1000000` and no override exists
- **THEN** `GET /backend-api/codex/models` reports `context_window=1000000` and `max_context_window=1000000` without `auto_compact_token_limit`

#### Scenario: Operator lowers a Claude window

- **WHEN** the model catalogue stores `350000` for that Claude model
- **THEN** the catalog reports `context_window=350000` and `max_context_window=350000`

#### Scenario: Native model unchanged

- **WHEN** no override exists for a Codex-native model with `context_window=272000` and `max_context_window=872000`
- **THEN** the catalog reports both upstream values unchanged

