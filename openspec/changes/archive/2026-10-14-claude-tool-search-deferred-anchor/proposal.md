## Why
Anthropic keeps the prompt cache when deferred tools are added, but not when a request goes from no deferred tool to one (CLIProxyAPI 97ba1e89). A translated Codex request declares no deferred tool until its first tool search loads one, and the `advanced-tool-use-2025-11-20` beta is sent only once a deferred tool exists. The first discovery in every Claude conversation therefore changes both and rewrites the whole cached prefix. Production shows it as a full miss after 753 s idle on the 1-hour tier, with tools, system and parameters unchanged (conversation 01a11bcc, 138,615 tokens written).

## What Changes
- A translated request that declares client tool search also declares one constant deferred anchor tool, `tool_search_deferred_anchor`, after the request's own tools and before tools loaded by search, as CLIProxyAPI does. Nothing ever references it.
- From the first search-capable request on, the request therefore has a deferred tool and sends the advanced-tool-use beta, so a discovery only appends a deferred tool.
- Requests without client tool search are unchanged.

## Capabilities
### Modified Capabilities
- `claude-accounts`: Claude client tool search declares a constant deferred anchor.

## Impact
Claude Responses projection. On deploy, each active search-capable Claude conversation misses the cache once, when the anchor first appears.
