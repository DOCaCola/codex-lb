## ADDED Requirements

### Requirement: Positional translated developer messages
Translated Responses developer and system messages that precede every conversation message SHALL form the system prompt with the request instructions. Later developer and system messages SHALL keep their conversation position: each SHALL be placed directly after the next user turn and before the following assistant turn or the end of the messages, never rewriting earlier messages, so later requests reproduce the same prefix. Models whose policy supports mid-conversation system messages SHALL receive them as `system` turns; other models SHALL receive their blocks unchanged between `<system-reminder>` delimiters at the end of that user turn. Requests containing system turns SHALL send the mid-conversation system beta. Signature recovery SHALL ignore system turns when protecting the open tool turn.

#### Scenario: Instruction update before a new prompt
- **WHEN** Codex sends a developer message after an assistant answer followed by the next user message, for a model with mid-conversation system support
- **THEN** Claude receives the developer content as a system turn directly after that user message, and the earlier messages are byte-identical to the previous request

#### Scenario: Update inside a tool loop
- **WHEN** a developer message follows a tool result and precedes the next tool call
- **THEN** the system turn sits between the tool-result user turn and the next assistant turn

#### Scenario: Update between assistant items
- **WHEN** a developer message arrives between two assistant items
- **THEN** it waits for the next user turn and is placed after it

#### Scenario: Model without system turns
- **WHEN** the model's policy lacks mid-conversation system support
- **THEN** the developer content closes the preceding user turn inside `<system-reminder>` delimiters and no system turn is sent

#### Scenario: Recovery behind a system turn
- **WHEN** a signature rejection is recovered for a request ending with a tool result followed by a system turn
- **THEN** the open tool turn keeps its signed thinking
