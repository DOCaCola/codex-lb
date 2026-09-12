# Responses request-body limits

Contract: [HTTP ingress specification](../openspec/specs/http-ingress-limits/spec.md).

For image-heavy Codex conversations on a memory-rich instance, configure:

```env
CODEX_LB_RESPONSES_BODY_LIMIT_BYTES=268435456
```

Restart the service after changing it. In Docker Compose, pass it through the service's `environment` and recreate the container; a Compose `.env` entry alone does not inject it into the container.

The default is 128 MiB. The supported range is 32–512 MiB, in bytes; invalid values fail startup. The setting applies to raw and decoded Responses/compact HTTP requests, the default downstream WebSocket message allowance, and expanded conversation replay. Explicit `--ws-max-size` or `UVICORN_WS_MAX_SIZE` overrides only the listener and can create a smaller transport limit.

Compression does not bypass decoded-body admission. Internal owner forwarding at `/internal/bridge/responses` also uses this budget; configure owner replicas consistently for the histories they serve. General HTTP and dedicated upload limits remain unchanged. Larger requests can consume several times their size in memory per concurrent request. Upstream limits still apply.

`inbound_body_too_large` means codex-lb rejected ingress; `outbound_body_too_large` means locally expanded replay exceeded the budget before dispatch. Neither is a provider context-window verdict. Errors name the budget and distinguish declared lengths from measured lower bounds. Raising this limit preserves image quality and history but does not ensure upstream acceptance.
