## ADDED Requirements

### Requirement: Model catalogue manages redirects

Settings > Models > Model catalogue MUST include a Redirects card listing requested model, served model and
status (active, or inactive with its reason) with add, change and delete actions. The requested model MUST
accept any slug and suggest catalogue models; the served-model picker MUST group eligible targets by provider
and mark hidden ones.

#### Scenario: Adding a redirect for a retired model
- **WHEN** the operator adds `gpt-5.4` redirecting to `gpt-5.5`
- **THEN** the card lists it as active

### Requirement: Catalogue rows mark redirect sources

Catalogue rows MUST include redirect sources marked "Redirects to <target>", keep their Client lists switch,
and show their context-window override as disabled while redirected. Compaction-route pickers MUST exclude
redirect sources.

#### Scenario: Retired model row
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5` for a slug outside the registry
- **WHEN** the catalogue renders
- **THEN** it shows a hidden `gpt-5.4` row marked "Redirects to gpt-5.5"

### Requirement: Request logs show redirected models

The request-log model cell MUST show `requested -> served` for redirected requests.

#### Scenario: Redirected request in the logs
- **GIVEN** a logged request for `gpt-5.4` served by `gpt-5.5`
- **WHEN** the logs page renders it
- **THEN** the model cell reads `gpt-5.4 -> gpt-5.5`
