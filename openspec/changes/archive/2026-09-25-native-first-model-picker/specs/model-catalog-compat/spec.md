## ADDED Requirements

### Requirement: Native models precede external models in the Codex picker

The Codex-native catalog MUST preserve native OpenAI model priorities and assign external model entries, including OpenRouter entries, consecutive priorities greater than every emitted native priority. External entries MUST retain their existing relative catalog order. This ordering MUST NOT change visibility, authorization, model identity, or routing. A catalog with no native entries MUST assign external priorities starting at zero.

#### Scenario: Client sorts a mixed catalog
- **WHEN** a client sorts a mixed native and external catalog by ascending priority
- **THEN** every native entry precedes every external entry
- **AND** native priorities remain unchanged

#### Scenario: Only external models are available
- **WHEN** the emitted catalog contains only external entries
- **THEN** their priorities start at zero and increase in catalog order
