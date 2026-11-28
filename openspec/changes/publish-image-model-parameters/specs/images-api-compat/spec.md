## ADDED Requirements

### Requirement: Image model parameter discovery
`/v1/models` SHALL describe image model request parameters in `image.supported_parameters`, each with a `type`, its
`values` or `min` and `max`, and optionally a `default` and `description`. OpenRouter models SHALL publish OpenRouter's
capabilities; OpenAI API models SHALL publish their documented family's parameters, or none outside documented
families. Descriptions SHALL NOT change Images request handling.

#### Scenario: Documented OpenAI API image model
- **WHEN** an enabled OpenAI API account selects `gpt-image-2.6-sunburst`
- **THEN** `/v1/models` lists `openai-apikey/gpt-image-2.6-sunburst` with `complexity` and with quality values up to `max`

#### Scenario: Undocumented OpenAI API image model
- **WHEN** an enabled OpenAI API account selects an image model outside the documented families
- **THEN** `/v1/models` lists it without `supported_parameters`

### Requirement: Native image model listing
`/v1/models` SHALL list the native `gpt-image-2` model with the parameters the Codex client sends to the native image
endpoint, unless the requesting API key may not use it or the Settings model catalogue hides it. With an active image
redirect it SHALL carry the redirect target's description; with an inactive redirect it SHALL NOT be listed.

#### Scenario: Native image model
- **WHEN** a client lists models without an image redirect for `gpt-image-2`
- **THEN** `gpt-image-2` is listed as an image model with `background`, `quality` and `size`

#### Scenario: Redirected native image model
- **WHEN** `gpt-image-2` redirects to an available OpenAI API image model
- **THEN** `gpt-image-2` is listed with the target model's parameter description

#### Scenario: Restricted API key
- **WHEN** an API key whose allowed models exclude `gpt-image-2` lists models
- **THEN** `gpt-image-2` is not listed
