# Classify terminal Claude unavailability

## Why

An Opus-to-Astra model switch with an expired Claude grant stalls in previous-model
compaction. Claude selection reports `reauth_required` as HTTP 503, so Codex's HTTP
retries delay its existing current-model compaction recovery. Waiting cannot repair
the grant. The installed 0.164.0-doca client immediately attempts the selected model
after an HTTP or WebSocket 400, with the original history retained.

## What Changes

- Return 400 invalid_request_error when every scoped routing exclusion requires
  operator action: paused source, non-ready credentials, disabled model or disallowed
  reasoning. Preserve the existing pool/owner code and diagnostics.
- Return400 invalid_request_error for explicitly disabled model sources and
  model memberships, including explicit compaction. Preserve source ownership
  and the existing WebSocket-to-HTTP transport handoff.
- Preserve 503 for temporary, mixed-temporary or unknown exclusions, and 429 for
  quota-only exhaustion. Do not report an upstream credential failure as client 401.
- Preserve account ownership; the gateway does not substitute another provider or
  choose a compaction model. The client owns recovery to the user-selected model.

## Impact

Claude routing diagnostics on Responses HTTP/WebSocket, native Messages and token
counting; shared disabled-source admission on Responses, Chat Completions and
explicit compaction. No schema, configuration, credential or history migration.
