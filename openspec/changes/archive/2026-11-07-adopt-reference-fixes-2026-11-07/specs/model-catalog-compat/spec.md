## ADDED Requirements

### Requirement: Empty provider discovery keeps the served catalog
OpenRouter, Claude and Antigravity catalog synchronization SHALL treat a
discovery reply that lists no models as a failed sync: it SHALL record a
catalog error and keep the previous snapshot and selections. Antigravity models
that the account's plan gates off SHALL still replace the catalog.

#### Scenario: Discovery answers with no models
- **WHEN** a provider's discovery reply lists no models
- **THEN** the account keeps its previous catalog and selected models stay routable
- **AND** the account shows a catalog error

#### Scenario: Plan gates every model off
- **WHEN** Antigravity lists models that the account's plan cannot call
- **THEN** the synchronized catalog offers none of them
