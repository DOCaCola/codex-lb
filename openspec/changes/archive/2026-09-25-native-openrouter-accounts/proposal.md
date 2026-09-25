## Why

Operators currently need LiteLLM to manage OpenRouter credentials and bridge Codex requests. Native accounts should synchronize the provider catalog, expose selected models and accurate balance information, and serve Codex WebSocket clients through the same dispatch pipeline as HTTP clients.

## What Changes

- Add OpenRouter account management backed by model sources, with encrypted inference and optional management credentials.
- Synchronize account-visible models, prices, capabilities and reasoning settings; preserve explicit selections and context limits.
- Display key allowance, account credits, free-request quota and freshness separately.
- Bridge client Responses WebSockets to source HTTP/SSE with shared policy, accounting, cancellation and continuation handling.
- Preserve provider tool protocols and reported costs; select eligible OpenRouter accounts and retry safely before response delivery.
- Start fresh: no automatic import of legacy LiteLLM routes or credentials and no automatic production cutover.

## Capabilities

### New Capabilities
- `openrouter-accounts`: Native account lifecycle, catalog synchronization, selection, quotas and provider protocol.

### Modified Capabilities
- `model-source-routing`: Shared source dispatch for HTTP and WebSocket clients, with bounded stateless continuation.

## Impact

Model-source persistence and migrations, proxy dispatch and WebSocket routing, background synchronization, Accounts and dashboard UI, API-key scoping, integration tests and operator documentation. Native ChatGPT credentials and routing remain separate.
