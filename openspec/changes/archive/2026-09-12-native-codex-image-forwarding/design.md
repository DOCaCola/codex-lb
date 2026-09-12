## Context

See proposal.md for the observed failure and source evidence. Codex sends standalone JSON image requests using its provider's ChatGPT credentials. Existing unary control transport already owns account authentication, configured egress routing and request-log persistence.

## Goals / Non-Goals

Keep native image execution independent of the conversation model source. Preserve public Images multipart and Responses-stream translation unchanged. No client setting, database migration, billing-provider fallback or production deployment is introduced.

## Decisions

- Split only the Codex-base routes. Share proxy policy and tracked image reservation settlement with the public adapter, but do not reuse its parameter matrix or response reconstruction.
- Extend the existing unary control path for the two explicit image operations. Use scoped quota-aware selection without the control path's quota-bypassing fallback, acquire an account response-create lease, refresh before dispatch, and do not enter post-dispatch retry branches.
- Preserve raw response bytes and safe metadata rather than converting errors into a generic image-tool envelope. Keep raw prompts/images out of payload traces. Bound response buffering to 100 MiB, including configured egress routes; disable redirect following.
- Reference image URLs stay opaque and are never fetched by codex-lb. This covers both filesystem data URLs and URLs reused from Codex conversation history.
- Settle only reported image token usage, including cached input tokens. Missing usage or failed requests release reservations through the existing tracked lifecycle. Cleanup is owned on cancellation and lease release is shielded.

## Risks / Trade-offs

- Account entitlement or native service availability can still fail: preserve the native error for the client; do not automatically change account or bill another provider.
- Clients can retry 5xx independently: avoid multiplying that with proxy-side image retries.
- Upstream may omit usage: do not invent token charges. Request logs retain the public model and HTTP status.
- Public SDK multipart and streaming contracts differ from Codex JSON: keep them on the existing adapter instead of expanding this change.

## Migration Plan

No schema or configuration migration. After explicit deployment approval, use the existing fork upgrade workflow. A separately authorized live generation/edit can verify account entitlement. Rollback uses the existing known-working revision workflow. No deployment or live generation is performed by this implementation.
