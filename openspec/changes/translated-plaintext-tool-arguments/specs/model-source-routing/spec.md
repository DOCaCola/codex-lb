## ADDED Requirements

### Requirement: Source tool calls declare plaintext arguments
Responses output forwarded from any model source SHALL mark each `function_call` whose tool declaration in the client request marks a parameter `encrypted` with `encrypted_function_args: []`, on non-stream payloads and on every streamed event carrying the item. Declarations SHALL be matched by the client's namespace and name, independent of provider wire aliases.

#### Scenario: OpenRouter subagent spawn
- **WHEN** an OpenRouter model calls the namespaced collaboration `spawn_agent` tool through an aliased wire name
- **THEN** the client receives the restored namespace and name with `encrypted_function_args: []`

#### Scenario: Generic source
- **WHEN** a non-OpenRouter source returns a call to a tool with an encrypted parameter
- **THEN** the forwarded call carries `encrypted_function_args: []`
