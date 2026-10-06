# openrouter-accounts Delta

## ADDED Requirements

### Requirement: OpenRouter assistant messages carry a Responses phase

OpenRouter Responses output SHALL deliver each assistant message with a Responses `phase`. A phase sent by OpenRouter
MUST be kept unchanged. A message without one SHALL receive `commentary` when another output item follows it. The last
such message of a completed response SHALL receive `final_answer`, or `commentary` when the response contains a
`function_call` or `custom_tool_call`. The last such message of an incomplete or failed response SHALL remain without a
phase. A streamed message's `response.output_item.done` SHALL be delivered once its phase is known, and the terminal
response output SHALL carry the same phases. When a stream ends or fails without a terminal event, a held message
SHALL be delivered without a phase before the stream ends.

#### Scenario: answer after commentary

- **WHEN** an OpenRouter model streams a message, a reasoning item and a second message, and the response completes
- **THEN** the first message is done with phase `commentary` before the reasoning item is added
- **AND** the second message is done with phase `final_answer`
- **AND** `response.completed` output and the replayed history carry the same phases

#### Scenario: message in a tool-requesting response

- **WHEN** a completed OpenRouter response ends with a message after a function call
- **THEN** that message has phase `commentary`

#### Scenario: truncated response

- **WHEN** an OpenRouter response is incomplete or failed after a message
- **THEN** its last message is done without a phase

#### Scenario: native phase

- **WHEN** OpenRouter sends an assistant message with a phase
- **THEN** the client receives the event unchanged
