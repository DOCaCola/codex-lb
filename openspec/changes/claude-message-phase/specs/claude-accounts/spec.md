# claude-accounts Delta

## ADDED Requirements

### Requirement: Translated assistant messages carry a Responses phase

A translated Claude response SHALL deliver each assistant message with the Responses `phase` that Claude's output
implies. A message SHALL stay open after its text block stops until its phase is known. A following text block SHALL
join the open message as a further `output_text` part, so at most one message is open. Any other valid content block
SHALL close the open message with phase `commentary` before that block's item is added. When Claude stops, the open
message SHALL close with phase `final_answer` for stop reasons `end_turn` and `stop_sequence`, and `commentary` for
`tool_use`. Truncated and paused stops, a refusal whose message was delivered, and streams that end without a stop
reason SHALL close it without a phase. When a stream fails, a message whose text finished SHALL be closed before the
error unless it is withheld behind a tool call. A rejected content block MUST NOT close the open message with a phase.

#### Scenario: answer after work

- **WHEN** Claude streams text, then a tool call, and stops with `tool_use`, and the next response streams text and
  stops with `end_turn`
- **THEN** the first message is done with phase `commentary` before the tool call item is added
- **AND** the second message is done with phase `final_answer`

#### Scenario: consecutive text blocks

- **WHEN** Claude streams two text blocks in a row and stops with `end_turn`
- **THEN** the client receives one message with two `output_text` parts and phase `final_answer`

#### Scenario: incomplete stop

- **WHEN** Claude stops with `max_tokens`, `pause_turn` or `model_context_window_exceeded` after text
- **THEN** the message is done without a phase and the response is incomplete

#### Scenario: failure after text

- **WHEN** a stream fails after a finished text block, because of an upstream error event, a rejected content block or
  a transport failure
- **THEN** the message is done without a phase before the error
