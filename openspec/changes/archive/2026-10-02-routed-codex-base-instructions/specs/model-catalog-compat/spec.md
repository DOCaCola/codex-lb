## ADDED Requirements

### Requirement: Routed Codex catalog entries carry the neutral Codex prompt
Codex catalog entries for Claude, OpenRouter and OpenAI-compatible source models SHALL carry, as `base_instructions`, the instruction template of the default listed native model: the listed native Codex catalog model with the lowest priority and a non-empty template, ties broken by slug. A native template is read from `model_messages.instructions_template`, or from the legacy `base_instructions` when no template is present. The GPT identity in that prompt MUST be neutralised and the prompt MUST NOT name a model. Selection MUST NOT depend on the requesting API key. When no native prompt exists, routed entries SHALL carry an empty prompt and the catalog build SHALL log a warning. Native entries are unchanged.

#### Scenario: Live native prompt available
- **GIVEN** listed native models with live prompts and an enabled Responses-capable source model
- **WHEN** a client calls `GET /backend-api/codex/models`
- **THEN** the source entry's `base_instructions` is the lowest-priority listed native prompt with "based on GPT-…" removed
- **AND** native entries keep their own prompts

#### Scenario: No native prompt
- **GIVEN** only native models without prompts, such as the bootstrap catalog
- **WHEN** a client calls `GET /backend-api/codex/models`
- **THEN** source entries carry an empty `base_instructions` and a warning is logged

### Requirement: Codex catalog size is checked against the client limit
The Codex catalog build SHALL log an error when the encoded `/backend-api/codex/models` body exceeds 1 MiB, the limit above which Codex rejects a `model_catalog_url` catalog and uses its bundled catalog.

#### Scenario: Oversized catalog
- **WHEN** the encoded Codex catalog exceeds 1 MiB
- **THEN** the build logs an error with the body size, the limit and the model count
