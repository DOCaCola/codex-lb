## ADDED Requirements

### Requirement: Input recorded during a tool step follows its results
Translated Claude Responses over HTTP and WebSocket SHALL hold a user message that
appears while tool calls are pending and SHALL place it after the step's last
tool result, in the same user turn, keeping held messages in input order. Tool
results SHALL open that user turn. An assistant step that appears while held input
still awaits results, and calls still pending at the end of the input, MUST fail
before dispatch with the parameter naming the first pending call's input item.
Retained history SHALL NOT be mutated.

#### Scenario: Goal-status notice recorded before a running call's result
- **WHEN** the input holds a call, a user notice, that call's result, then a user message
- **THEN** Claude receives the tool_use, then one user turn with the tool_result, the notice and the message in that order

#### Scenario: Assistant step before the held input's results
- **WHEN** an assistant item appears after held input while its calls remain pending
- **THEN** the request fails before dispatch with the parameter naming the pending call
