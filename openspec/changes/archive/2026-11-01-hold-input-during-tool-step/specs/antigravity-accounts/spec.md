## ADDED Requirements

### Requirement: Input recorded during a tool step follows its responses
Antigravity Responses projection SHALL hold a user message that appears while
tool calls are pending and SHALL place it in the user turn after the step's
function responses, keeping held messages in input order. A model step that
appears while held input still awaits responses, and calls still pending at the
end of the input, MUST fail before dispatch with the parameter naming the first
pending call's input item.

#### Scenario: Goal-status notice recorded before a running call's result
- **WHEN** the input holds a call, a user notice, that call's result, then a user message
- **THEN** the function response follows the call and one user turn carries the notice and the message
