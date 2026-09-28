# Proposal

## Why
OpenRouter's Inceptron endpoint rejects flattened Codex MCP tool names exceeding
64 characters. Client identities must survive provider wire-name constraints.

## What Changes
- Introduce request-scoped deterministic aliases for OpenRouter tool identities.
- Restore original names and namespaces in complete and streamed responses.
- Apply the same identities to historical calls and explicit tool selection.

## Capabilities
### New Capabilities
None.
### Modified Capabilities
- openrouter-accounts: bounded reversible tool identities.

## Impact
OpenRouter Responses and Chat forwarding, protocol tests and specs. No production
change, migration, retry change or model/provider routing change.
