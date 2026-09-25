## Context

See proposal.md. ModelSource already owns encrypted credentials, per-model settings, client-key scoping and request accounting. Account is subscription-specific. Responses sources currently force client HTTP fallback. OpenRouter Responses supports custom tools and namespaces but rejects stored continuations.

## Goals / Non-Goals

Serve OpenRouter directly and preserve Codex client WebSockets. Keep subscription account selection independent. No legacy credential import, automatic model substitution, production deployment, or hosted image/audio implementation in this change.

## Decisions

- Add an OpenRouter extension table keyed by ModelSource id. Its typed JSON snapshot stores the discovered catalog and monitoring observations; selected ModelSourceModel rows remain the routing projection. Credentials remain encrypted and never enter responses or logs.
- Keep selection overrides separate from discovered metadata. Refresh every six hours, monitor balances every minute, and offer manual refresh. Only successful complete catalog reads replace availability; failures retain the last snapshot with a visible error.
- Fix the OpenRouter origin to its official HTTPS API. Validate inference credentials at `/key`; use a separate optional management key for `/credits`. Preserve unknown values and distinguish shared credits from key allowance.
- Use native upstream Responses, with explicit model-id mapping, provider parameter policy, reasoning and tool capabilities. Catalog prices are estimates; upstream usage.cost is authoritative when present.
- Share source HTTP dispatch through an in-process request adapter for WebSocket turns. Reuse policy enforcement, source admission, cancellation and settlement. Native subscription frames retain their existing path. No internal network loopback or recursive proxy requests.
- Generalize bounded continuation retention for source requests. Resolve complete client history before provider shaping, retain complete output before exposing completion, scope by client key and conversation, and reject expired or unreadable state. Preserve source-owned summaries during model switches.
- Try eligible accounts only before content delivery; respect source assignment scope, Retry-After and model/account error scope. No silent switch to another model.

## Risks / Trade-offs

- Provider schema support does not prove every model implements every tool: exercise native Responses with representative contract fixtures and an optional live smoke test.
- Continuations contain conversation data: reuse bounded private storage, current one-hour retention and cancellation-safe publication; do not rely on dashboard log retention.
- Management credentials have broad authority: optional, encrypted, and used only for read-only credit monitoring.
- Catalog changes can retire models: keep operator selection visible but unavailable and never substitute a paid model.

## Migration Plan

Add a forward migration with a single parent and upgrade/downgrade tests. Existing generic sources keep their behavior. Configure fresh OpenRouter accounts after deployment and separately remove the legacy LiteLLM source during explicit production cutover.
