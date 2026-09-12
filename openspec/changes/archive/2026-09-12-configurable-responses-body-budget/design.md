# Design

Adapt OpenCodex #4138's bounded configuration and provenance diagnostics, not its silent clamping. Pydantic validates startup configuration. Existing cached process settings own the budget; a shared resource-policy accessor serves middleware, CLI default, and replay. Compact routes use the same history admission budget as Responses. General admission and dedicated multipart parsers remain unchanged.

Local Responses ingress returns 413/inbound_body_too_large. Expanded replay returns a non-retryable 400/outbound_body_too_large without claiming provider context exhaustion. Diagnostics distinguish declared wire lengths, observed wire lower bounds, and decoded lower bounds. No transcript text or image data is logged. Explicit --ws-max-size/UVICORN_WS_MAX_SIZE retains its existing listener-only precedence.

Configuration changes require restart. A deployment may opt into 268435456 bytes (256 MiB); upstream transport/provider limits remain independent. The internal `/internal/bridge/responses` owner-forwarding endpoint also uses the shared budget so multi-replica handoff does not retain a hidden 32 MiB cap. Configure owner replicas consistently for the histories they serve. No automatic image pruning, retries, or production rollout.
