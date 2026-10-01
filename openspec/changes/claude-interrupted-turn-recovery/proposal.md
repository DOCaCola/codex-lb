# Proposal

## Why

An interrupted Claude response leaves Codex history ending in an assistant progress message. A retry then reaches Anthropic as unsupported assistant prefill. The initiating undeclared-tool projection error also escapes the source WebSocket bridge instead of delivering a structured failure.

## What Changes

- Preserve translated assistant-tail history and append a wire-only user continuation after validating tool-result completeness.
- Keep explicit user/tool-result endings, native Messages and logical retained history unchanged.
- Serialize source Responses stream forwarding failures after exactly-once settlement so HTTP and WebSocket clients receive an error without a successful completion or automatic generation retry.
- Add bounded, content-free undeclared-tool diagnostics without tool-name guessing or relaxation of declaration validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: History-preserving translated continuation and undeclared-tool diagnostics.
- `model-source-routing`: Structured post-start Responses errors after settlement.

## Impact

Claude request/response projection, shared source Responses transport composition, protocol and public HTTP/WebSocket regression tests. No migrations, configuration switches, new dependencies, client patches or production deployment.
