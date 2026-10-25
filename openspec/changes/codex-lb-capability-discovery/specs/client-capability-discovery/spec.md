## ADDED Requirements

### Requirement: codex-lb capability document
The proxy SHALL serve `GET /backend-api/codex/codex-lb/capabilities` and `GET /v1/codex-lb/capabilities`, so the document resolves relative to any Codex provider base URL that targets codex-lb. The response SHALL be a JSON object with `object` set to `codex_lb.capabilities`, `service` set to `codex-lb`, and `capabilities` listing the client features codex-lb serves. The endpoint SHALL apply the same proxy API-key authentication as the Codex model catalog. `composer_predictions` SHALL be listed, because Codex desktop prediction forks are ordinary Responses turns.

#### Scenario: Desktop integration probes a provider
- **WHEN** a client requests `<base_url>/codex-lb/capabilities` with valid proxy credentials
- **THEN** the response identifies codex-lb and lists `composer_predictions`

#### Scenario: Missing credentials
- **WHEN** API-key authentication is enabled and the request carries no valid key
- **THEN** the proxy rejects it with `invalid_api_key`, like the model catalog
