## ADDED Requirements

### Requirement: Provider-attributed source errors
Gateway-generated error messages for a model-source request SHALL name the provider that serves it: "Claude" for Claude accounts, "OpenRouter" for OpenRouter accounts and "OpenAI-compatible model source" for generic sources. Error codes, statuses and upstream-provided messages SHALL remain unchanged.

#### Scenario: Claude connection failure
- **WHEN** a Claude account's request fails to resolve its upstream host
- **THEN** the message reads "Claude request failed: ClientConnectorDNSError" with code `model_source_unreachable`

#### Scenario: Generic source timeout
- **WHEN** a generic OpenAI-compatible source misses its header deadline
- **THEN** the message names the OpenAI-compatible model source
