# Merge Responses Lite Tool Bundles

## Why

With Responses Lite (every GPT-6 and gpt-5.6 model in the catalog), Codex records each change of its tool catalog as
an `{"type": "additional_tools", "role": "developer", "tools": [...]}` input item and keeps it in history. After a
switch to Claude the client replays those items, and the translator rejected the first request with
"Unsupported Claude Responses item: additional_tools" (production, 2026-10-17 22:57:41Z, Luna 6 to Opus 5.5). Model
sources are advertised without Responses Lite, but forwarding passed the items to them unchanged.

Lite also groups plain functions under the reserved `functions` namespace, which Codex treats as no namespace
(`ToolRouter::build_tool_call`); calls from the Lite era may carry it.

References: CLIProxyAPI `responsesToolSources` (top-level tools, then `additional_tools` items, then
`tool_search_output`; one winner per name), OmniRoute `collectResponsesTools` (top-level wins on named collisions,
same-named namespaces merge; also applied to its same-format grok-cli lane), CLIProxyAPI's xAI executor (merges bundles
into `tools` because xAI rejects the item), and opencodex/OmniRoute flattening the reserved `functions` namespace.

## What Changes

- A shared projection merges bundled declarations after the top-level tools: top-level declarations unchanged, then
  each bundle in history order; the first declaration of a tool wins, same-named namespaces merge their members,
  nameless hosted tools are identified by type, and members of the reserved `functions` namespace merge as
  top-level tools.
- The Claude translator declares the merged tools, skips the bundle items in the conversation and resolves tools
  declared or called under the `functions` namespace as tools without a namespace.
- Model-source Responses forwarding merges bundles into `tools`, drops the items and removes the reserved namespace
  from recorded calls. Claude's cache-preserving source compaction keeps the bundles with the other declarations.

## Capabilities

### Modified Capabilities

- `claude-accounts`: Responses Lite tool bundles.
- `model-source-routing`: Responses Lite tool bundles.
