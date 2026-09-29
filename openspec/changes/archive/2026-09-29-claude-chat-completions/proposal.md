# Proposal

## Why

Claude OAuth models are available through Responses and Messages but not `/v1/chat/completions`, so standard Chat clients cannot use enrolled Claude accounts.

## What Changes

- Route Chat messages for Claude models through the existing Responses-to-Claude dispatcher, retaining its admission, retries, accounting, and cleanup ownership.
- Translate Chat request controls and Claude output to Chat format with explicit unsupported-control and incomplete-result behavior.
- Preserve existing OpenAI-compatible Chat and native Claude Messages routes.

## Capabilities

- `chat-completions-compat`: Claude Chat request and response projection.
- `claude-accounts`: Claude OAuth Chat routing and ownership.

## Impact

Proxy routing, Chat conversion, Claude protocol projection, tests, specs, and user documentation. No migration or new dependency.
