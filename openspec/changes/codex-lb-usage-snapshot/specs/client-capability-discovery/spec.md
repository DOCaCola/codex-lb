## MODIFIED Requirements

### Requirement: codex-lb capability document
The proxy SHALL serve `GET /backend-api/codex/codex-lb/capabilities` and `GET /v1/codex-lb/capabilities`, so the document resolves relative to any Codex provider base URL that targets codex-lb. The response SHALL be a JSON object with `object` set to `codex_lb.capabilities`, `service` set to `codex-lb`, and `capabilities` listing the client features codex-lb serves, each as an object with an `id` and the `models` it applies to. The endpoint SHALL apply the same proxy API-key authentication as the Codex model catalog. `composer_predictions` SHALL be listed with the native subscription models available to the requesting key: those the operator's accounts can serve and the key's model allowlist permits. Models served by routed model sources, such as Claude and OpenRouter, MUST NOT be listed, so desktop predictions stay off for their threads. `usage` SHALL be listed with every model a quota pool of the usage snapshot serves to the requesting key, unless the operator hides upstream quota from API-key clients.

#### Scenario: Desktop integration probes a provider
- **WHEN** a client requests `<base_url>/codex-lb/capabilities` with valid proxy credentials
- **THEN** the response identifies codex-lb and lists `composer_predictions` with the native models available to that key

#### Scenario: Routed source model
- **WHEN** a Claude or OpenRouter model is enabled in the catalog
- **THEN** it is absent from the `composer_predictions` models and listed among the `usage` models

#### Scenario: Key with a model allowlist
- **WHEN** the requesting key may only use some native models
- **THEN** `composer_predictions` lists only those models

#### Scenario: Upstream quota hidden from API keys
- **WHEN** the operator hides upstream quota from API-key clients
- **THEN** the document omits the `usage` capability

#### Scenario: Missing credentials
- **WHEN** API-key authentication is enabled and the request carries no valid key
- **THEN** the proxy rejects it with `invalid_api_key`, like the model catalog

## ADDED Requirements

### Requirement: Usage snapshot endpoint
The proxy SHALL serve `GET /backend-api/codex/codex-lb/usage` and `GET /v1/codex-lb/usage` with the proxy API-key authentication of the capability document. The response SHALL be a JSON object with `object` set to `codex_lb.usage`, `generated_at`, `pools` and `today`, built from stored quota readings and request logs only. The endpoint MUST NOT refresh usage from any provider, and SHALL answer 403 while the operator hides upstream quota from API-key clients.

#### Scenario: Polling the snapshot
- **WHEN** a client requests the snapshot repeatedly
- **THEN** each response reflects the readings codex-lb already stored and no provider usage request is made

#### Scenario: Upstream quota hidden
- **WHEN** the operator hides upstream quota from API-key clients
- **THEN** the endpoint answers 403

### Requirement: Usage snapshot pools
Each pool SHALL be one independently limited quota stating its kind, a label, the models it serves to the requesting key, its account count, how many accounts no quota window blocks, its windows, when its newest reading was taken and whether its readings are stale. A window SHALL state its length, the percentage left and the soonest reset of an account with usage in it.

#### Scenario: Thread served by Claude
- **WHEN** a desktop integration fetches the snapshot and the open thread uses a Claude model
- **THEN** the Claude pool lists that model with its 5-hour and weekly windows and their refill times

### Requirement: Usage snapshot weekly outlook
A weekly window SHALL add the dashboard weekly pace's outlook over the pool's accounts: when recent burn spends the pool before relief arrives, and the next relief with the percentage left after it.

#### Scenario: Pool runs dry before its reset
- **WHEN** the recent burn spends the Claude pool before its weekly reset
- **THEN** the weekly window reports when it runs dry and that the reset refills it

### Requirement: Usage snapshot pool composition
The snapshot SHALL list a pool only when it serves a model to the key. The ChatGPT accounts available to the key SHALL be pooled like the Codex rate-limit headers, leaving out a window only blocked accounts report while another account is ready. Claude SHALL be pooled like the Claude rate-limit headers, with a separate pool for models whose model-specific weekly window reads differently. Antigravity SHALL form one pool per model family. OpenRouter SHALL report prepaid credits and no windows.

#### Scenario: Weekly-blocked account with an unused 5-hour window
- **WHEN** the only ChatGPT account reporting a 5-hour window has spent its week while another account can serve
- **THEN** the ChatGPT pool reports its weekly window and leaves out the 5-hour window

#### Scenario: Model-specific Claude limit binds
- **WHEN** an account's Fable weekly window is more used than its shared seven-day window
- **THEN** the Fable model forms its own Claude pool with that window

### Requirement: Usage snapshot daily totals
The request SHALL carry `since`, the start of the client's day as a timestamp with a time zone no more than 25 hours ago, and any other value SHALL be rejected with a validation error. `today` SHALL report the requesting key's request count and estimated cost since `since`, and SHALL be null when the request carries no API key.

#### Scenario: Requests since local midnight
- **WHEN** a key made two requests since `since` and one before it
- **THEN** `today` counts the two requests and their estimated cost

#### Scenario: Day start outside the last day
- **WHEN** `since` lies more than 25 hours ago or has no time zone
- **THEN** the proxy rejects the request with a validation error
