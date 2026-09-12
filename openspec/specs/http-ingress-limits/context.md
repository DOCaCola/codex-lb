# Responses body admission

The Responses byte budget protects process memory, not the model's token window. Images encoded in history can exceed it even when compressed HTTP bytes fit. One observed client request contained 51 embedded images and exceeded the default decoded budget during compaction.

`CODEX_LB_RESPONSES_BODY_LIMIT_BYTES` is a T1 per-instance resource setting: replicas can have different memory allocations. It defaults to 134217728 bytes (128 MiB), accepts 33554432 through 536870912 bytes inclusive, and requires restart. Invalid values fail configuration rather than silently clamping. The legacy removed `CODEX_LB_MAX_DECOMPRESSED_*` variables remain removed.

For a memory-rich deployment, `CODEX_LB_RESPONSES_BODY_LIMIT_BYTES=268435456` admits up to 256 MiB per raw/decoded Responses or compact body. This also sets the default downstream WebSocket message allowance and expanded replay ceiling. Explicit `--ws-max-size` / `UVICORN_WS_MAX_SIZE` continues to override only the listener; use the shared setting to avoid accidental transport mismatch. The shipped CLI must be used for listener defaults.

The internal `/internal/bridge/responses` owner-forwarding endpoint shares this budget; configure owner replicas consistently for the histories they serve. The general 32 MiB budget and dedicated multipart parser limits do not change. Neither request content nor upstream limits are changed. Admission does not guarantee upstream acceptance. Peak memory can be several times the budget per concurrent request because decoding, JSON parsing, and replay retain copies.

Responses ingress returns 413 / `inbound_body_too_large`; expanded replay returns 400 / `outbound_body_too_large`. These identify local resource refusal, not a provider context verdict. Diagnostics contain only byte counts, budget, and measurement provenance. A declared wire length is client-supplied; streamed/decoded measurements are lower bounds because counting stops when the cap is crossed. Typed-body exception handling preserves the same response and logs it once.

Design reference: OpenCodex PR #4138 (bounded configurable admission and distinct local diagnostics). This adaptation deliberately retains codex-lb's default and unrelated route policies, and rejects invalid configuration.
