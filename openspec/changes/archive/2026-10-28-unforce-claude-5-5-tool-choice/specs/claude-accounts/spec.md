## ADDED Requirements

### Requirement: Forced tool choice on models that reject it

Opus 5.5 and Sonnet 5.5, dated snapshots included, reject `tool_choice` `any` and `tool`. For these models every
Messages and token-counting request, native, translated or helper, SHALL be forwarded with `tool_choice.type` `auto`,
without `tool_choice.name`, and with `disable_parallel_tool_use`, tools, thinking and messages unchanged. The rewrite
SHALL be recorded as the `tool_choice_auto` transformation and logged with the model. Forced tool choice SHALL be
forwarded unchanged for every other model. The Responses translation SHALL NOT reject forced tool choice combined with
thinking for these models, and SHALL keep rejecting it for others.

#### Scenario: Forced tool on Opus 5.5

- **WHEN** a request to Opus 5.5 carries `tool_choice` `{"type":"tool","name":"lookup","disable_parallel_tool_use":true}` with adaptive thinking
- **THEN** upstream receives `{"type":"auto","disable_parallel_tool_use":true}` and the adaptive thinking configuration

#### Scenario: Token counting

- **WHEN** a token-counting request to Sonnet 5.5 carries `tool_choice` `any`
- **THEN** upstream receives `tool_choice` `auto`

#### Scenario: Older model

- **WHEN** a request to Opus 5 carries a forced tool choice
- **THEN** it is forwarded unchanged

#### Scenario: Responses turn with required tools and reasoning

- **WHEN** a Responses turn to Opus 5.5 sets `tool_choice` `required` with reasoning effort `high`
- **THEN** the turn is accepted and forwarded with `tool_choice` `auto` and adaptive thinking
