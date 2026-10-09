## ADDED Requirements

### Requirement: OpenAI-compatible providers are managed as accounts
User-defined `openai_compatible` model sources SHALL be created, listed,
selected, renamed, coloured, paused, resumed, edited and deleted on the Accounts
page alongside Codex, Claude and OpenRouter accounts, and SHALL NOT be managed
from Settings. Their detail SHALL show usage trends from
`GET /api/model-sources/{id}/trends`, the models with their pricing and the
connection details. `openai_compatible` SHALL be a provider identity for account
colours, provider marks and request-log attribution. Mutation controls SHALL be
unavailable to read-only sessions.

#### Scenario: Add an endpoint
- **WHEN** an operator chooses "API endpoint" in the add-account chooser
- **THEN** the OpenAI-compatible provider dialog opens and the created source appears in the Accounts list

#### Scenario: Settings no longer lists sources
- **WHEN** an operator opens Settings → Models
- **THEN** only the model catalogue is shown and no model-source request is issued

### Requirement: Provider-backed sources refuse model-source management
The model-source API SHALL refuse to update or delete a source whose kind is not
`openai_compatible` with a 400 that names the Accounts dashboard as the place to
manage it, leaving the source and its provider account unchanged.

#### Scenario: Deleting a Claude-backed source
- **WHEN** a client calls `DELETE /api/model-sources/{id}` for a Claude-backed source
- **THEN** the response is 400 and the Claude account and its source remain
