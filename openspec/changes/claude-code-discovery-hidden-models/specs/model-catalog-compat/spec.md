## MODIFIED Requirements

### Requirement: Claude Code discovers Messages-servable models

The Anthropic models list SHALL contain exactly the models the API key may use through `/v1/messages` whose catalog visibility is `list`: native OpenAI models, Claude models, and models of enabled sources that support Responses. The list is Claude Code's model picker, so catalog-hidden models SHALL be omitted; they remain usable when requested by name. Claude models SHALL be listed by their Anthropic ID without the `anthropic/` prefix. Every other model SHALL be listed under its `clb-claude-` alias, so Claude Code's discovery filter keeps it. Each entry SHALL have `type` `model`, `id`, a `display_name` naming the real model, a `description` naming its provider, and `created_at`; `max_input_tokens` and `max_tokens` SHALL be included when known. Entries SHALL be ordered OpenAI models, then Claude models, then other models. The response SHALL contain every entry, with `has_more` `false` and `first_id`/`last_id` naming the first and last entries.

#### Scenario: Claude Code discovers a GPT model
- **WHEN** Claude Code calls `GET /v1/models?limit=1000` with an `anthropic-version` header and `gpt-6.1-sol` is available
- **THEN** the list contains `clb-claude-gpt-6.1-sol` with a display name naming `gpt-6.1-sol`

#### Scenario: Source model with slashes
- **WHEN** a Responses-capable source serves `openrouter/z-ai/glm-5.3-flash`
- **THEN** the list contains `clb-claude-openrouter~sz-ai~sglm-5.3-flash`

#### Scenario: Claude model keeps its ID
- **WHEN** a Claude account serves `anthropic/claude-opus-5-5`
- **THEN** the list contains `claude-opus-5-5`

#### Scenario: Chat-only source model omitted
- **WHEN** a source that supports only Chat Completions serves `local-coder`
- **THEN** the list does not contain an entry for `local-coder`

#### Scenario: Catalog-hidden model omitted
- **WHEN** the catalog marks `codex-auto-review` with visibility `hide`
- **THEN** the Anthropic list does not contain `clb-claude-codex-auto-review`
- **AND** the OpenAI-shaped `/v1/models` list still contains `codex-auto-review`

#### Scenario: API key visibility
- **WHEN** the API key's allowed models exclude `gpt-6-astra`
- **THEN** the list does not contain `clb-claude-gpt-6-astra`
