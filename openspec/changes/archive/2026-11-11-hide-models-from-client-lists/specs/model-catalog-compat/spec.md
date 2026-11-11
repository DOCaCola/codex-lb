## ADDED Requirements

### Requirement: Client model lists omit operator-hidden models

The service SHALL serve a slug that an operator hid in the Settings model catalogue in the Codex catalog with its full metadata and priority and with `visibility` `hide`, for every API key, and SHALL omit it from `data`, the OpenAI-shaped `/v1/models` list and the Anthropic models list, including its Fast entry. Catalog builds SHALL read hidden slugs once per build from a snapshot invalidated through the cross-replica `settings` namespace.

#### Scenario: Hidden native model keeps its metadata
- **GIVEN** `gpt-5.6-sol` is hidden
- **WHEN** a Codex client calls `GET /backend-api/codex/models`
- **THEN** the `gpt-5.6-sol` entry has `visibility` `hide` and the same context window, reasoning levels and instructions as when listed
- **AND** `data` does not contain `gpt-5.6-sol`

#### Scenario: Hidden source model leaves every picker
- **GIVEN** `anthropic/claude-fable-5-2` is hidden
- **WHEN** clients call the OpenAI-shaped `/v1/models` and the Anthropic models list
- **THEN** neither list contains the model

#### Scenario: Per-key allowlist does not list a hidden model
- **GIVEN** `gpt-6-sol` is hidden and an API key with `apply_to_codex_model` allows `gpt-6-sol`
- **WHEN** that key fetches the Codex catalog
- **THEN** `gpt-6-sol` has `visibility` `hide`

#### Scenario: Database unreachable
- **GIVEN** hidden slugs were loaded and the database becomes unreachable past the snapshot's TTL
- **WHEN** a catalog is built
- **THEN** the last known hidden slugs keep applying

### Requirement: Hiding a model does not change its availability

Hiding SHALL NOT change request routing on any endpoint, API-key model authorization, account model selection, compaction routes, pricing, context-window overrides, the routed base instructions, or which catalog entry supplies the slug's metadata.

#### Scenario: Hidden model remains usable
- **GIVEN** `gpt-5.6-sol` is hidden
- **WHEN** a client sends a Responses request for `gpt-5.6-sol`
- **THEN** it is routed exactly as if the model were listed

#### Scenario: Hidden Claude model through Messages
- **GIVEN** `anthropic/claude-fable-5-2` is hidden
- **WHEN** Claude Code requests `claude-fable-5-2` through `/v1/messages`
- **THEN** the request is served

#### Scenario: Routed instructions ignore hiding
- **GIVEN** the lowest-priority listed native model is hidden
- **WHEN** the Codex catalog is built
- **THEN** source entries carry the same `base_instructions` as before hiding

### Requirement: Operators manage hidden models through the settings API

Hidden slugs SHALL be stored one row per slug in `hidden_models`. `GET /api/settings/model-context-window-overrides` SHALL report `listed` per catalogue model. `PUT /api/settings/hidden-models/{slug}` SHALL hide idempotently, rejecting slugs outside the catalogue with 400 `model_not_in_catalogue`; `DELETE` SHALL list again, 404 `hidden_model_not_found` when not hidden. Writes SHALL require dashboard write access and be audited.

#### Scenario: Listing a model again
- **GIVEN** `gpt-5.6-sol` is hidden
- **WHEN** `DELETE /api/settings/hidden-models/gpt-5.6-sol` succeeds
- **THEN** the next catalog request on every replica lists `gpt-5.6-sol`
- **AND** a `settings_changed` audit event names `hidden_models` and the slug

#### Scenario: Hiding a model outside the catalogue
- **WHEN** `PUT /api/settings/hidden-models/unknown-model` is called
- **THEN** the response is 400 with code `model_not_in_catalogue` and no row is written

#### Scenario: Model leaves and returns
- **GIVEN** `gpt-5.6-sol` is hidden
- **WHEN** it leaves the catalogue and later returns
- **THEN** it is still hidden
