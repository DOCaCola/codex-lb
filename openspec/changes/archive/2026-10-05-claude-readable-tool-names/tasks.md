## 1. Implementation
- [x] 1.1 Add the request-local Claude tool name registry with OmniRoute's Claude Code mappings, CLIProxyAPI namespace qualification, numbered collisions and digest-shortened long names
- [x] 1.2 Project declarations, history calls and forced tool choice through the registry
- [x] 1.3 Resolve Claude tool calls by wire name or unique client name, once per content block

## 2. Verification
- [x] 2.1 Unit tests for mapping, namespaces, `mcp__` passthrough, collisions, long names, unique and ambiguous client names, history replay, tool choice and undeclared rejection
- [x] 2.2 Update existing Claude protocol, schema, search and integration tests to the new wire names
