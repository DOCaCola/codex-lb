## ADDED Requirements

### Requirement: Native compaction can run on a configured model

The dashboard MUST manage native compaction routes as one row per coding model in `model_compaction_routes`
(`slug`, `compaction_model`, `reasoning_effort` or `null`). A route MUST be compatible to be stored or applied:
both models are native subscription models in the model registry that are offered to accounts and not suppressed; they
differ, or the route sets an effort; they declare the same non-empty `comp_hash` and the same `use_responses_lite`;
the compaction model's context ceiling (its `max_context_window`, else its `context_window`) is at least the context
window clients receive for the coding model after overrides; the compaction model's input modalities include every
input modality of the coding model; a configured effort is one the compaction model supports; and the compaction model
has no route of its own. `GET /api/settings/model-compaction-routes` MUST list the eligible native models with their
supported efforts and every route with `status` `"active"` or `"inactive"` and the incompatibility `reason`;
`PUT /api/settings/model-compaction-routes/{slug}` MUST create or replace a compatible route and reject an incompatible
one with 400 `compaction_route_incompatible`; `DELETE` MUST remove it (404 `compaction_route_not_found` when absent).
Each write MUST be audited as `settings_changed` naming `model_compaction_routes` and the slug, and MUST invalidate the
cached route snapshot through the cross-replica `settings` namespace.

A native compaction request is a Responses request whose last top-level input item is `compaction_trigger`, or a
`/responses/compact` request. When its model, after API-key model enforcement and alias normalization, has a route that
is compatible with the current catalog, the proxy MUST replace `model` with the compaction model and, when the route
sets an effort and the API key enforces none, `reasoning.effort` with that effort, before effort policy and
unsupported-effort normalization, on every Responses surface (HTTP, WebSocket, owner-forwarded, non-streaming and
`/responses/compact`). Nothing else in the request changes. Routing, continuity, account model allow-lists, request
logs and costs MUST then use the compaction model. The route MUST NOT apply to non-compaction requests, to an API key
whose allowed models exclude the compaction model, or to a route the current catalog makes incompatible; each skipped
route and each applied route MUST be logged with the coding model, the compaction model and the reason or effort.

#### Scenario: Compaction runs on the configured model

- **GIVEN** a route `gpt-6-astra -> gpt-6-luna` with effort `low` and both models sharing `comp_hash`
- **WHEN** a Codex client sends `gpt-6-astra` at effort `high` with input ending in `compaction_trigger`
- **THEN** upstream receives `model=gpt-6-luna` and `reasoning.effort=low` with the input, tools and instructions unchanged
- **AND** the request log records `gpt-6-luna` for the compaction

#### Scenario: Ordinary turns keep the coding model

- **GIVEN** the same route
- **WHEN** the client sends `gpt-6-astra` without a terminal `compaction_trigger`
- **THEN** upstream receives `gpt-6-astra` unchanged

#### Scenario: Incompatible route is rejected and skipped

- **WHEN** `PUT` stores a compaction model whose `comp_hash` differs, whose ceiling is below the coding model's window,
  or whose effort list lacks the configured effort
- **THEN** the response is 400 with code `compaction_route_incompatible` and no row is written
- **WHEN** a stored route becomes incompatible after a catalog refresh
- **THEN** compaction requests keep the coding model, the skip is logged with the reason, and the settings API lists the
  route as `inactive` with that reason

#### Scenario: API-key policy wins

- **GIVEN** an API key whose allowed models exclude the compaction model, or that enforces an effort
- **WHEN** it sends a compaction request on a routed coding model
- **THEN** the excluded key keeps the coding model, and the effort-enforcing key keeps its enforced effort
