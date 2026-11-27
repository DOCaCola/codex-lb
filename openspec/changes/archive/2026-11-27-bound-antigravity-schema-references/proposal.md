## Why

Cloud Code takes function parameters in Gemini's OpenAPI dialect, which has no `$ref`, so the Antigravity compiler copies every local reference into place. Its complexity limit counted compiled schema nodes, not their content. A shared definition with a long enum or description is therefore copied whole for each reference: locally, a 0.16 MB tool schema compiled to 129 MB. A crafted or badly generated MCP schema could inflate one request by orders of magnitude.

References agree on the cause and differ only on the response:

- OmniRoute bounds material copied by expansion per schema and per request and rejects the request when exceeded (`schemaBudget.ts`: 256 KiB per schema, 2 MiB and 50,000 nodes per request; schemas without `$ref` are never charged).
- CLIProxyAPI caps copied bytes at 256 KiB per schema, then silently replaces further references with a type hint; opencodex caps nodes and widens the schema; sub2api has no bound.
- No reference sends raw `parametersJsonSchema` to Antigravity; CLIProxyAPI renames it onto `parameters`. The native CLI 1.5.18 keeps MCP schemas with references intact, but a mock capture could not show how it declares them, so forwarding references remains unqualified.

## What Changes

- Compiled nodes that come from a `$ref` target are charged with their own UTF-8 size and one node. Literal data inside them (enum values, descriptions, property names) now counts.
- One request may copy at most 256 KiB per tool schema and 2 MiB and 50,000 nodes across all its tool schemas. Exceeding either fails the request as `unsupported_parameter` on the tool that crossed the limit; the schema is never weakened.
- Schemas without references are not charged; the existing per-schema node and depth limits are unchanged.

## Impact

- Spec: `antigravity-accounts`.
- Code: `app/modules/antigravity/tool_schema.py`, `app/modules/antigravity/protocol.py`.
- No settings, schema or client changes. Production has carried no Antigravity traffic yet.
