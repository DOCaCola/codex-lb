## ADDED Requirements

### Requirement: Claude models support Codex client-side tool search

The model catalog SHALL advertise `supports_search_tool` for Claude models.
When a translated request declares a client-executed `tool_search` tool, the
service SHALL declare it to Claude as `ToolSearch`, translate each
`tool_search_call` into an assistant `tool_use` and each `tool_search_output`
into a `tool_result` containing one `tool_reference` per loaded tool, and
declare every loaded tool once with `defer_loading: true`. Deferred tools SHALL
NOT carry a cache breakpoint and SHALL NOT count toward the cache-lineage tool
shape. A request with deferred tools SHALL send the
`advanced-tool-use-2025-11-20` beta. A streamed `ToolSearch` call SHALL be
returned as a client `tool_search_call` with its parsed arguments.

#### Scenario: Loaded tools stay out of the cached prefix

- **GIVEN** a Codex request that declares `shell` and `tool_search` and whose history loaded `canvas_open` through tool search
- **WHEN** it is sent to a Claude account
- **THEN** the upstream request declares `canvas_open` with `defer_loading: true` and without `cache_control`, the search result is a `tool_reference` to it, and the advanced-tool-use beta is sent

#### Scenario: Claude searches for a tool

- **GIVEN** a Claude response that calls `ToolSearch` with a query
- **WHEN** it is streamed to Codex
- **THEN** Codex receives a `tool_search_call` with `execution: client` and the query as arguments

#### Scenario: Loaded tools without search are ordinary

- **GIVEN** a request whose history loaded a tool but which no longer declares `tool_search`
- **WHEN** it is sent to a Claude account
- **THEN** the loaded tool is declared without `defer_loading`
