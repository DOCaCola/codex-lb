## ADDED Requirements

### Requirement: Claude Code-shaped translated tool names
Translated client tools SHALL be sent to Claude under Claude Code-shaped wire names: the Claude Code canonical name when the flat client name has a known mapping, otherwise the PascalCase form of the name. Names starting with `mcp__` and names already in Claude Code form SHALL be kept. Namespaced tools SHALL first be qualified as `namespace__name`. Wire names that collide SHALL be numbered in declaration order, and names that do not satisfy Anthropic's tool-name constraint SHALL be shortened with a stable digest of the qualified name. A request-local table SHALL restore the client's name, namespace and tool kind on every returned call. History tool calls and forced tool choice SHALL use the same wire name as the declaration.

#### Scenario: Known harness tool
- **WHEN** a client declares `terminal` or `read_file`
- **THEN** Claude receives `Bash` or `Read`, and the call it returns reaches the client as `terminal` or `read_file`

#### Scenario: Namespaced tool
- **WHEN** a client declares `spawn_agent` in the `collaboration` namespace
- **THEN** Claude receives `CollaborationSpawnAgent`, and the returned call carries the original name and namespace

#### Scenario: Collision
- **WHEN** two declared tools map to the same wire name
- **THEN** the later one receives a numbered wire name and both resolve to their own client identity

#### Scenario: Replayed history
- **WHEN** history contains a call to a declared tool
- **THEN** the replayed `tool_use` carries the declaration's wire name

## MODIFIED Requirements

### Requirement: Bounded undeclared Claude tool diagnostics
Claude tool calls SHALL resolve by wire name, or by the client's own qualified tool name when exactly one tool in the request has it. Other names, including a client name shared by several tools, SHALL fail explicitly without further alias guessing or client-side execution. Diagnostics SHALL identify source, model, response, content index, declaration count and a bounded name fingerprint; a bounded syntactically safe tool name MAY also be recorded. Arguments, call IDs, conversation contents and credentials MUST NOT be logged.

#### Scenario: Unknown tool after text
- **WHEN** Claude emits an undeclared tool after an assistant progress message
- **THEN** the tool is rejected with content-free identity diagnostics and no tool-call event for that tool reaches the client

#### Scenario: Unsafe name
- **WHEN** the rejected name contains control characters, unsupported characters or excessive length
- **THEN** only its fingerprint and safe structural metadata are logged

#### Scenario: Client name used by Claude
- **WHEN** Claude calls `write_stdin` and the request declared exactly one tool with that name
- **THEN** the call resolves to that tool

#### Scenario: Ambiguous client name
- **WHEN** Claude calls a client name that several declared tools share
- **THEN** the call is rejected as undeclared
