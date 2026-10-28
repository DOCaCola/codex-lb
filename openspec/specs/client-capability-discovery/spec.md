# client-capability-discovery Specification

## Purpose
Let Codex clients discover which codex-lb features a provider serves, and for which models, without assuming a fork-specific build.

## Requirements

### Requirement: codex-lb capability document
The proxy SHALL serve `GET /backend-api/codex/codex-lb/capabilities` and `GET /v1/codex-lb/capabilities`, so the document resolves relative to any Codex provider base URL that targets codex-lb. The response SHALL be a JSON object with `object` set to `codex_lb.capabilities`, `service` set to `codex-lb`, and `capabilities` listing the client features codex-lb serves, each as an object with an `id` and the `models` it applies to. The endpoint SHALL apply the same proxy API-key authentication as the Codex model catalog. `composer_predictions` SHALL be listed with the native subscription models available to the requesting key: those the operator's accounts can serve and the key's model allowlist permits. Models served by routed model sources, such as Claude and OpenRouter, MUST NOT be listed, so desktop predictions stay off for their threads.

#### Scenario: Desktop integration probes a provider
- **WHEN** a client requests `<base_url>/codex-lb/capabilities` with valid proxy credentials
- **THEN** the response identifies codex-lb and lists `composer_predictions` with the native models available to that key

#### Scenario: Routed source model
- **WHEN** a Claude or OpenRouter model is enabled in the catalog
- **THEN** it is absent from the `composer_predictions` models

#### Scenario: Key with a model allowlist
- **WHEN** the requesting key may only use some native models
- **THEN** `composer_predictions` lists only those models

#### Scenario: Missing credentials
- **WHEN** API-key authentication is enabled and the request carries no valid key
- **THEN** the proxy rejects it with `invalid_api_key`, like the model catalog
