## ADDED Requirements

### Requirement: Request logs record the requested model of a redirect

Request logs MUST keep the served model in `model` and MUST record the model after API-key enforcement in
a nullable `requested_model` only when a redirect applied. The request-log API MUST return
`requested_model`, and its model filter MUST match either column. Pricing, reports and account
attribution MUST use `model`.

#### Scenario: Redirected request
- **GIVEN** a redirect `gpt-5.4 -> gpt-5.5`
- **WHEN** a request for `gpt-5.4` completes
- **THEN** its log has `model` `gpt-5.5`, `requested_model` `gpt-5.4` and `gpt-5.5` pricing

#### Scenario: Filtering by the requested model
- **WHEN** the logs are filtered by `gpt-5.4`
- **THEN** redirected requests for `gpt-5.4` are included
