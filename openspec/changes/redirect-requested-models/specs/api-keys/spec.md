## ADDED Requirements

### Requirement: Model restrictions apply to the requested model of a redirect

When a redirect applies, API-key `allowed_models` MUST be checked against the requested model after
API-key model enforcement and before the redirect, and MUST NOT be checked against the served model.
Model-scoped limits and usage accounting MUST use the served model. `/v1/models` filtering MUST keep
using the listed slug.

#### Scenario: Allowlist names the retired model
- **GIVEN** an API key allowing only `gpt-5.4` and a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** the key requests `gpt-5.4`
- **THEN** the request is served by `gpt-5.5`

#### Scenario: Allowlist names only the target
- **GIVEN** an API key allowing only `gpt-5.5` and a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** the key requests `gpt-5.4`
- **THEN** the request is rejected as a model the key may not use
