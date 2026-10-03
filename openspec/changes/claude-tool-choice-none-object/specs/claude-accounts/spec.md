## ADDED Requirements

### Requirement: Claude tool-choice directive forms
The Claude projection SHALL accept `auto`, `none` and `required` tool-choice
directives in string or single-field object form with identical semantics,
retaining tool declarations. It SHALL send `disable_parallel_tool_use` only with
choices that permit tool use, and SHALL treat only `required` and named-tool
choices as forced when thinking is enabled. Directive objects with additional
fields SHALL be rejected. Native OpenAI passthrough SHALL remain unchanged.

#### Scenario: Object-form none
- **WHEN** a client sends `tool_choice: {"type": "none"}` with declared tools
- **THEN** Claude receives `{"type": "none"}` with the tools still declared

#### Scenario: None without parallel tool use
- **WHEN** a client sends `none` with `parallel_tool_calls: false`
- **THEN** the Claude tool choice carries no parallel-use flag

#### Scenario: Thinking with object-form none
- **WHEN** a client enables reasoning and sends `tool_choice: {"type": "none"}`
- **THEN** the request is projected with thinking enabled

#### Scenario: Malformed directive object
- **WHEN** a directive object carries fields besides `type`
- **THEN** the request fails with an unsupported tool choice error
