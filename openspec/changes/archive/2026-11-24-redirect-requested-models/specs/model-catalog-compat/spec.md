## ADDED Requirements

### Requirement: Redirects are validated when stored

Redirects MUST be stored one row per requested model in `model_redirects` (`source_model`, `target_model`).
A write MUST be rejected with 400 `model_redirect_invalid` and a reason, without writing, unless the source
is a valid slug different from the target, the target is a catalogue model servable for text generation, and
the target is not itself a redirect source.

#### Scenario: Redirecting a retired model
- **GIVEN** `gpt-5.4` is not in the model registry and `gpt-5.5` is a native catalogue model
- **WHEN** a redirect `gpt-5.4 -> gpt-5.5` is stored
- **THEN** it is accepted

#### Scenario: Chains and self-redirects are rejected
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** `gpt-5.3 -> gpt-5.4` or `gpt-5.5 -> gpt-5.5` is stored
- **THEN** the response is 400 with code `model_redirect_invalid` and no row is written

### Requirement: Operators manage redirects through the settings API

`GET /api/settings/model-redirects` MUST list each redirect with `status` (`active`/`inactive`), its
`reason` and the eligible targets by provider. `PUT .../{source}` MUST create or replace a redirect;
`DELETE` MUST remove it (404 `model_redirect_not_found` when absent). Writes MUST require dashboard write
access, be audited as `settings_changed` naming `model_redirects`, and invalidate the cross-replica snapshot.

#### Scenario: Storing a redirect
- **WHEN** `PUT /api/settings/model-redirects/gpt-5.4` stores target `gpt-5.5`
- **THEN** the next request on every replica uses the redirect
- **AND** a `settings_changed` audit event names `model_redirects` and `gpt-5.4`

#### Scenario: Deleting an absent redirect
- **WHEN** `DELETE /api/settings/model-redirects/gpt-5.4` is called without a stored redirect
- **THEN** the response is 404 with code `model_redirect_not_found`

### Requirement: Redirects and compaction routes do not overlap

A redirect whose source is the coding model or the compaction model of a compaction route, and a compaction
route whose coding or compaction model is a redirect source, MUST be rejected with 400
`model_redirect_conflict` by the respective settings API.

#### Scenario: Redirecting a routed coding model
- **GIVEN** a compaction route `gpt-6-astra -> gpt-6-luna`
- **WHEN** a redirect with source `gpt-6-astra` or `gpt-6-luna` is stored
- **THEN** the response is 400 with code `model_redirect_conflict`

### Requirement: Requested models resolve once

The proxy MUST resolve a request's model in this order: suffix-alias normalization, API-key model
enforcement, the active redirect of that model, the compaction route of the served model, then effort policy.
Model-source selection, provider routing guards, account selection, continuity, effort normalization,
pricing and request logs MUST use the served model, and no component may resolve the enforced model
separately. Each applied redirect MUST be logged with both models and the surface.

#### Scenario: Responses turn is served by the target
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** a Codex client sends a WebSocket turn for `gpt-5.4`
- **THEN** upstream receives `model=gpt-5.5` with the input, tools and instructions unchanged
- **AND** the turn is routed to an account offered `gpt-5.5`

#### Scenario: Redirect to a model source
- **GIVEN** a redirect `gpt-5.4 -> openrouter/z-ai/glm-5.3-flash`
- **WHEN** a client requests `gpt-5.4`
- **THEN** the request is dispatched exactly as a request for `openrouter/z-ai/glm-5.3-flash`

#### Scenario: Enforced model is redirected
- **GIVEN** an API key enforcing `gpt-5.4` and a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** the key sends a `/v1/messages` request
- **THEN** `gpt-5.5` serves it and no routing guard rejects it as not matching the enforced model

#### Scenario: Compaction route of the served model applies
- **GIVEN** a redirect `gpt-6-sol-legacy -> gpt-6-astra` and a compaction route `gpt-6-astra -> gpt-6-luna`
- **WHEN** a client sends `gpt-6-sol-legacy` with input ending in `compaction_trigger`
- **THEN** upstream receives `gpt-6-luna`

### Requirement: Redirects cover text-generation surfaces

Redirects MUST apply to Codex Responses over HTTP and WebSocket (owner-forwarded, non-streaming,
`/responses/compact`, compaction-trigger turns and client prewarm), `/v1/responses`, `/v1/chat/completions`,
and Anthropic `/v1/messages` and `count_tokens`. Images, transcriptions, embeddings, realtime and internal
jobs MUST NOT be redirected.

#### Scenario: Chat completions
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** a client calls `/v1/chat/completions` with `gpt-5.4`
- **THEN** `gpt-5.5` serves it

#### Scenario: Image requests
- **GIVEN** a redirect whose source is an image model slug
- **WHEN** a client calls the images API with that slug
- **THEN** the request is not redirected

### Requirement: An inactive redirect fails explicitly

When a redirect's target is no longer in the catalogue or is itself redirected, requests for its source MUST fail with 400
`model_redirect_target_unavailable` naming both models and MUST NOT be sent on the source model. The
settings API MUST list the redirect as `inactive` with that reason.

#### Scenario: Target left the catalogue
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5` and `gpt-5.5` leaves the catalogue
- **WHEN** a client requests `gpt-5.4`
- **THEN** the response is 400 with code `model_redirect_target_unavailable`
- **AND** the settings API lists the redirect as `inactive`

### Requirement: Redirected responses expose no served-model header

Responses and WebSocket handshakes for redirected requests MUST NOT carry an `OpenAI-Model` header, so Codex
raises no model-reroute warning. Response bodies MUST keep the served model.

#### Scenario: Codex sees no reroute warning
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** a Codex client is served over HTTP or WebSocket
- **THEN** no response or handshake carries an `OpenAI-Model` header

### Requirement: Catalogs serve a redirect source with its target's metadata

While a redirect is active, the Codex catalog, `/v1/models` and the Anthropic models list MUST serve the
source with the target's rendered metadata (context window after the target's override, reasoning levels,
input modalities, capabilities, instructions), using the source as `slug`/`id` and its registry display
name when one exists, else the slug. Overrides stored for the source MUST NOT apply. Rendering MUST NOT
depend on account availability.

#### Scenario: Retired source carries the target's metadata
- **GIVEN** a redirect `gpt-5.4 -> claude-opus-5-5`
- **WHEN** a Codex client fetches the catalog
- **THEN** the `gpt-5.4` entry has Claude Opus 5.5's context window, reasoning levels and instructions

### Requirement: Redirect sources follow the hide switch

Redirect sources MUST be catalogue rows governed by `hidden_models`. Creating a redirect for a slug outside
the model registry MUST hide that slug; creating one for a registry model MUST keep its visibility.

#### Scenario: Retired source is hidden by default
- **WHEN** a redirect `gpt-5.4 -> gpt-5.5` is created and `gpt-5.4` is not in the registry
- **THEN** the Codex catalog serves `gpt-5.4` with `visibility` `hide`

### Requirement: Inactive redirects are absent from client catalogs

While a redirect is inactive, client catalogs MUST omit its source. After the redirect is removed, catalogs
MUST restore the source's own entry when the registry has one. The target's own entry remains unchanged.

#### Scenario: Inactive source still appears in the registry
- **GIVEN** a current native model redirects to a model that leaves the catalogue
- **WHEN** a client fetches a model catalog
- **THEN** the redirect source is absent

#### Scenario: Removing a redirect restores the source
- **GIVEN** a redirect `gpt-5.5 -> gpt-6-sol` where `gpt-5.5` is a registry model
- **WHEN** the redirect is deleted
- **THEN** the next catalog on every replica serves `gpt-5.5` with its own metadata
