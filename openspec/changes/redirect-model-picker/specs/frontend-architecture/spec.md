## MODIFIED Requirements

### Requirement: Model catalogue manages redirects

Settings > Models > Model catalogue MUST include a Redirects card listing requested model, served model and
status (active, or inactive with its reason) with add, change and delete actions. Both model fields MUST use a
searchable model picker with sections. The requested-model picker MUST accept any slug, list client-requested image
models in a separate highlighted section ahead of the provider catalogues, and offer a "Show disabled models" switch
that adds unpublished provider models, marked as not enabled. The served-model picker MUST stay disabled until a
requested model is chosen, group eligible targets by provider, mark hidden ones, and offer image targets for image
sources and text targets otherwise.

#### Scenario: Adding a redirect for a retired model
- **WHEN** the operator adds `gpt-5.4` redirecting to `gpt-5.5`
- **THEN** the card lists it as active

#### Scenario: Redirecting the image backend
- **GIVEN** an OpenAI API account with `gpt-image-2.6-sunburst` enabled
- **WHEN** the operator chooses `gpt-image-2` from the client requests section
- **THEN** the served-model picker offers `openai-apikey/gpt-image-2.6-sunburst` and no text models
