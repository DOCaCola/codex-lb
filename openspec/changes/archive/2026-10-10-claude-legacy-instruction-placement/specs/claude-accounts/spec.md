## ADDED Requirements

### Requirement: Claude instruction placement follows the legacy model list

Instruction placement SHALL treat a Claude model as legacy only when its base
identifier, without the `anthropic/` prefix or a date suffix, is one of Claude
3.5 Haiku, Claude 3.7 Sonnet (including their `-latest` aliases), Claude Haiku
4.5, Claude Opus 4, 4.1, 4.5, 4.6 and 4.7, or Claude Sonnet 4, 4.5 and 4.6.
Legacy models SHALL receive relocated and positional instructions as
`<system-reminder>` user content; every other model, including models the
service does not know, SHALL receive them as mid-conversation `system` turns.
A request SHALL NOT be refused because its model is not listed, and structured
output SHALL be forwarded without a per-model gate.

#### Scenario: Newly released model

- **WHEN** an OAuth request with caller instructions targets `claude-haiku-5-5`, which no table lists
- **THEN** the instructions are sent as a mid-conversation `system` turn and the request is dispatched

#### Scenario: Legacy model

- **WHEN** caller instructions target `claude-haiku-4-5-20251001`
- **THEN** they are sent between `<system-reminder>` delimiters in user content and no `system` turn is sent

#### Scenario: Structured output on an unlisted model

- **WHEN** a translated request asks for a JSON-schema text format on `claude-fable-5-1`
- **THEN** the schema is forwarded as `output_config.format` and Anthropic decides whether the model supports it
