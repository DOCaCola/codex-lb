# Proposal

## Why

Production OpenRouter GLM requests returned 403 before the operator enabled key funding, then 400 with only “Provider returned error”. Generic credential recoding and loss of nested provider diagnostics prevent distinguishing access policy from malformed requests.

## What Changes

- Preserve OpenRouter HTTP 403 status and sanitized rejection messages without asserting invalid credentials.
- Extract bounded, allowlisted provider diagnostics from OpenRouter error metadata into the message retained by clients and request logs.
- Keep credential protection for unknown OpenAI-compatible sources and generic upstream 401 handling.
- Bound OpenRouter error reads and redact credentials before truncation or exposure.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `openrouter-accounts`: safe and useful provider rejection diagnostics.

## Impact

OpenRouter error projection, shared source forwarding, regression tests and documentation. No deployment, database migration, configuration change or production inference replay.
