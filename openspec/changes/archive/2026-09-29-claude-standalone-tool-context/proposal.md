## Why
The Claude Responses adapter rejects every tool output without a preceding pending call. Codex can legitimately carry standalone tool outputs as delegation or imported conversation context; rejecting these prevents the request from reaching Anthropic. Production logged this rejection on 2026-09-29, but did not retain enough diagnostics to distinguish standalone context from duplicate or out-of-order results.

## What Changes
Classify translated tool outputs before Messages projection. Preserve standalone output content as explicitly labeled user context without fabricating a tool call or result. Continue rejecting malformed identifiers, duplicate results, results preceding their calls and interrupted/incomplete tool cycles. Add content-free failure diagnostics and public HTTP/WebSocket regression coverage.

## Capabilities
### Modified Capabilities
- `claude-accounts`: explicit portable standalone tool-output projection.

## Impact
Claude Responses projection only. Authenticated continuation expansion, signed-history ownership, native Messages forwarding, account settings and storage remain unchanged. No deployment or schema migration.
