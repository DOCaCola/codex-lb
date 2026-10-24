## MODIFIED Requirements

### Requirement: Messages routing by model

Authenticated `/v1/messages` and `/v1/messages/count_tokens` SHALL first decode a `clb-claude-` model alias to the model it names: `~s` becomes `/` and `~t` becomes `~`, and any other `~` sequence or an empty name SHALL fail with an Anthropic `invalid_request_error`. They SHALL then apply the API key's enforced model. Model names starting with `anthropic/` or `claude-` SHALL use the native Claude route. Any other name SHALL be resolved as a Responses model the API key may use, served by a native account or an enabled Responses-capable model source, and SHALL be served by translation. A model the API key may not use SHALL fail before dispatch with an Anthropic `permission_error`. Any other failure to serve the model SHALL be the error `/v1/responses` returns for it, as an Anthropic error envelope. No Claude account is selected for a translated model. Request logs, limits, pricing and reasoning envelopes SHALL use the routed model; the response SHALL report the model as the client sent it.

#### Scenario: Claude Code requests a GPT model
- **WHEN** Claude Code sends a Messages request for `gpt-6.1-sol`
- **THEN** the request is served by an OpenAI account through translation and no Claude account is selected

#### Scenario: Claude Code requests a discovered alias
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt-6.1-sol`
- **THEN** the request is served and logged as `gpt-6.1-sol`
- **AND** the response reports the model `clb-claude-gpt-6.1-sol`

#### Scenario: Invalid alias
- **WHEN** Claude Code sends a Messages request for `clb-claude-gpt~x`
- **THEN** the client receives an Anthropic `invalid_request_error` before any upstream request

#### Scenario: Claude model unchanged
- **WHEN** Claude Code sends a Messages request for `claude-opus-5-5`
- **THEN** it uses the native Claude route as before

#### Scenario: Unauthorized model
- **WHEN** the API key's allowed models exclude the requested non-Claude model
- **THEN** the client receives an Anthropic `permission_error` before any upstream request

#### Scenario: Unknown model
- **WHEN** the model resolves to neither a Claude model nor a model any account or source serves
- **THEN** the client receives the `/v1/responses` error for that model as an Anthropic error envelope
