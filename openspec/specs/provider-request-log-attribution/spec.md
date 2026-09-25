# Provider request-log attribution

## Purpose
Identify provider accounts consistently in request logs without conflating provider sources with native OpenAI accounts.

## Requirements

### Requirement: Provider request attribution
Request logs SHALL display a recorded provider source using its current permitted name or retained source ID, including deleted sources. Unassigned SHALL mean neither native account nor provider source identity exists. Request details SHALL expose the same attribution. Provider identity SHALL take precedence when a source ID is recorded.

#### Scenario: OpenRouter rejection
- **WHEN** an OpenRouter log has a source ID and no native account ID
- **THEN** the account cell and details identify that source rather than Unassigned

### Requirement: Provider account filters
Account filter options SHALL include provider sources present in matching logs using source-prefixed values distinct from native account IDs. Selection SHALL filter by source ID and return accurate totals, including mixed selections and deleted sources. Authorized free-text search SHALL match provider names. Names SHALL respect account-identity permissions and email privacy settings.

#### Scenario: Same ID across identity domains
- **WHEN** native and provider records share the same ID text
- **THEN** selecting source-prefixed identity matches only the provider's requests

#### Scenario: Restricted principal
- **WHEN** a principal lacks account identity permission
- **THEN** provider names are neither returned nor searchable
