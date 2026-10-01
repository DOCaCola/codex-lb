## ADDED Requirements

### Requirement: Translated tool calls declare plaintext arguments
When a translated Claude function call targets a tool whose declaration marks any parameter `encrypted`, every public Responses representation of that call (streamed added and done items and final output, over HTTP and WebSocket) SHALL carry `encrypted_function_args: []`. Calls to tools without encrypted parameters and custom tool calls SHALL NOT carry the field.

#### Scenario: Subagent spawn from Claude
- **WHEN** Claude calls the collaboration `spawn_agent` tool whose `message` parameter is declared encrypted
- **THEN** the client receives the call with `encrypted_function_args: []` and delivers the message to the child as plaintext

#### Scenario: Ordinary tool
- **WHEN** Claude calls a function whose parameters declare no encryption
- **THEN** the call carries no `encrypted_function_args` field
