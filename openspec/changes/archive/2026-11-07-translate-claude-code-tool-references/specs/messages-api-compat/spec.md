## ADDED Requirements

### Requirement: Messages tool search results
Translated Messages requests SHALL render each `tool_reference` block in a
tool result as a text part `Tool loaded: <name>` in content order, naming the
tool as the translated request declares it. Each marker SHALL end with a line
break and start with one after text that does not. A reference without a tool
name SHALL be rejected. References MUST NOT add or authorize tools; deferred
tools remain ordinary functions.

#### Scenario: ToolSearch loads tools
- **WHEN** a tool result contains only `tool_reference` blocks for Read and a long MCP tool
- **THEN** the function output carries `Tool loaded: Read` and `Tool loaded:` with the MCP tool's alias, each on its own line

#### Scenario: Reference without a name
- **WHEN** a `tool_reference` block has no tool name
- **THEN** the request fails with `invalid_request_error`
