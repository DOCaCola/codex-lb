## ADDED Requirements

### Requirement: Claude Code Fast selectors for OpenAI models

Claude Code discovery SHALL list, directly after each listed OpenAI account model whose catalog offers the priority
service tier, a sibling entry with the ID `clb-claude-<escaped model>~fast`, the display name and description
suffixed with ` · Fast`, and the same limits. Fast entries SHALL NOT be listed while Fast Mode is prohibited or when
the API key enforces a service tier, and SHALL NOT be listed for model-source or Claude models. Decoding SHALL treat a
terminal `~fast` as the Fast marker before decoding the escaped name. A Messages request naming a Fast selector SHALL
be served as the named model with `service_tier: "priority"`, subject to Fast Mode policy; a Fast selector for a
model whose catalog does not offer the priority tier SHALL fail before dispatch with `invalid_request_error`.

#### Scenario: Fast row listed
- **WHEN** Claude Code discovers models and `gpt-5.6-sol` offers the priority tier
- **THEN** `clb-claude-gpt-5.6-sol~fast` follows `clb-claude-gpt-5.6-sol` with a ` · Fast` display name

#### Scenario: Fast selector served
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt-5.6-sol~fast`
- **THEN** upstream receives `gpt-5.6-sol` with `service_tier: "priority"`
- **AND** the response reports `clb-claude-gpt-5.6-sol~fast`

#### Scenario: Model without Fast
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt-5.4~fast` and `gpt-5.4` offers no priority tier
- **THEN** it receives `invalid_request_error` before any upstream request

#### Scenario: Fast Mode prohibited
- **WHEN** Fast Mode is prohibited
- **THEN** discovery lists no Fast entries
