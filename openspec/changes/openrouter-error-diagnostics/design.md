# Design

## Context

See proposal. Existing request logs store the normalized error message, not arbitrary OpenRouter metadata. Unknown compatible sources intentionally discard 401/403 bodies because they can contain masked credentials.

## Goals / Non-Goals

Preserve useful, safe OpenRouter rejection diagnostics on HTTP and WebSocket routes. Do not change retries, account selection, production configuration or expose entire provider bodies. Do not infer that funding caused the historical 403: this is operator-supplied likely context, not retained upstream evidence.

## Decisions

- Exempt only native OpenRouter 403 from generic credential recoding; keep 401 and unknown-source behavior unchanged.
- Bound OpenRouter HTTP error bodies to 64 KiB. Unparseable or oversized bodies retain status with a generic diagnostic, not a partial raw dump.
- Normalize a small allowlist (message, code, type, param); add provider name and a structured metadata.raw error message/code/param to the main message so existing logs retain it. Do not return metadata, headers, prompt echoes or arbitrary raw fields.
- Redact the exact configured key and recognizable/masked key tokens before truncating. Reuse shared rendered-secret redaction for bearer, keyed and URL credentials. Cap projected message length. Unknown raw formats are not echoed.
- Reuse this normalization for image errors. No raw-body passthrough borrowed from references.

## Reference evidence (2026-09-28)

- OpenCodex `3cc34e1181926b64331490fdcfee162ffb62fe73`: `src/server/chat-native.ts` reads bounded error bodies and uses redacted detail; source inspection, not live reproduction.
- OmniRoute `a58000c7685f4091c7a6fd8ddf3ebce7d2ec67c3`: `open-sse/utils/error.ts` and `errorSanitization.ts` expose sanitized upstream_details with size/depth/field controls. Its classifier distinguishes several non-auth 403 causes. Best reference for safe diagnostic projection, not proof of specialized OpenRouter metadata.raw flattening.
- CLIProxyAPI `acdace936fa7df2905500c7f5e0a97d683138dea`: `internal/runtime/executor/openai_compat_executor.go` retains original status and body in statusErr, plus Retry-After. Useful preservation principle; raw passthrough is inappropriate for our secret-bearing gateway.
- Sub2API `9a62841fd124d026cf3694fcf9b79e98addcdbdc`: generic error extraction and sanitized ops/client handling, including JSON nested inside error.message. No dedicated OpenRouter metadata.raw handling established.

No implementation copied. These references preserve more evidence than our discarded 403 body, but do not identify the historical GLM 400 cause.

## Risks / Trade-offs

Provider messages can contain secrets → exact and pattern redaction, fixed field selection, bounded reads, regression tests. Some unknown provider formats lose detail intentionally. Persisting improved messages only helps new requests; historical discarded bodies cannot be recovered.

## Migration Plan

No migration or configuration needed; no deployment in this task.
