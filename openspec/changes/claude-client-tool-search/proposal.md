## Why
Codex desktop side chats lose the parent's tool allow-list and declare 11 extra `mcp__codex_app__*` tools. Because Claude caches tools first, that one difference invalidates the whole cached prefix: one side chat wrote 205,653 tokens at the 1-hour rate ($1.66). Codex already avoids this for OpenAI models with client-side tool search, which keeps MCP tools out of the declared list until the model loads them. For Claude models codex-lb doesn't advertise tool search, so Codex sends every tool directly.

## What Changes
The model catalog advertises `supports_search_tool` for Claude models, so Codex declares a client-executed `tool_search` tool and defers its MCP tools. The Claude adapter translates that protocol into Anthropic's custom tool search:

- `tool_search` is declared as the Claude Code `ToolSearch` tool.
- A `tool_search_call` in history becomes an assistant `tool_use`. A `tool_search_output` becomes a `tool_result` whose content is `tool_reference` blocks.
- Each loaded tool is declared once with `defer_loading: true`, so it stays out of the cached prefix.
- A streamed `ToolSearch` call is returned to Codex as a client `tool_search_call` with parsed arguments.

Requests that defer tools send the `advanced-tool-use-2025-11-20` beta, as Claude Code does. The cache breakpoint, and the cache-miss diagnostics, ignore deferred tools.

## Capabilities
### Modified Capabilities
- `claude-accounts`: Claude models support Codex client-side tool search with deferred tools.

## Impact
The Claude protocol and response translation, cache placement, cache-lineage shapes, the Claude dispatch beta header and the model catalog. Codex clients start deferring MCP tools for Claude models after they refresh the catalog. There is no schema change.
