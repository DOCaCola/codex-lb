## ADDED Requirements

### Requirement: Relocated OAuth instructions follow the leading user run

When OAuth instruction relocation places the caller's system blocks in a
mid-conversation `system` turn, the service SHALL insert that turn after the
leading run that starts with the first ordinary user turn. User turns and
effort directives (system turns with empty content and an `output_config`)
SHALL continue the run; any other turn SHALL end it. The relocated turn
SHALL therefore precede an assistant turn, another content-bearing system
turn, or the end of `messages`, and no existing message SHALL be rewritten
or reordered.

#### Scenario: Request after client compaction

- **GIVEN** messages consisting of a user summary, an effort directive and a new user message
- **WHEN** instructions are relocated for a model with mid-conversation system support
- **THEN** the relocated system turn is the last message

#### Scenario: Consecutive user turns

- **GIVEN** messages starting with two user turns followed by an assistant turn
- **WHEN** instructions are relocated
- **THEN** the relocated system turn sits between the second user turn and the assistant turn

#### Scenario: Single leading user turn

- **GIVEN** messages starting with one user turn followed by an assistant tool call
- **WHEN** instructions are relocated
- **THEN** the relocated system turn directly follows that user turn, as before
