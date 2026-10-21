## ADDED Requirements

### Requirement: Translated Claude requests carry no blank text

Translated Claude Responses over HTTP and WebSocket SHALL NOT project a text part that is empty or contains only
whitespace. This SHALL apply to message content, paired and standalone tool outputs, external task input, code-mode
notifications, reasoning summaries and instructions; the remaining content SHALL keep its order. A user or assistant
message without remaining content SHALL be omitted and MUST NOT interrupt or satisfy a pending tool call. A paired tool
output without visible content SHALL be a `tool_result` with empty string content, and a later code-mode notification
for that call SHALL replace it. Projection MUST NOT invent placeholder text and MUST NOT mutate logical history. Native
Messages requests SHALL remain unchanged.

#### Scenario: Codex replays blank content
- **WHEN** a translated request contains blank instructions, a blank user part, a blank assistant message before a
  tool call, a blank reasoning summary or a blank tool output
- **THEN** Claude receives no blank text block and no empty message
- **AND** the blank tool output is a `tool_result` with empty string content

#### Scenario: A blank user message during a tool cycle
- **WHEN** a blank user message arrives between a tool call and its output
- **THEN** it is omitted and the tool output still pairs with its call

#### Scenario: A notification follows a blank exec result
- **WHEN** a code-mode notification follows an `exec` result without visible content in the open result turn
- **THEN** the notification's content becomes that result's content
