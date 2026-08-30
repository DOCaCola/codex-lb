## Context

Codex normally resends the full conversation on a WebSocket turn. codex-lb uses
an in-memory continuity record to replace the already accepted input prefix
with `previous_response_id`, reducing the next upstream frame to a delta. The
record currently contains no model identity.

This becomes unsafe when the client changes models. In the observed failure, a
completed native `gpt-5.6-sol` turn seeded the continuity record. The client
then submitted an unanchored 64-item replay for an OpenRouter model. codex-lb
injected the native response id, trimmed the replay to three items, resolved the
native subscription owner, and bypassed the source-to-HTTP guard.

## Goals / Non-Goals

**Goals:**

- Treat a proxy-injected response id as an optimization owned by the model
  selector that established it.
- Keep the client's complete replay intact across a model transition.
- Let the existing source guard and HTTP retry perform provider selection from
  the current model.
- Preserve same-model continuity compression and stale-anchor recovery.

**Non-Goals:**

- Override recorded ownership for a client-supplied `previous_response_id`.
- Add a proxy-wide local Responses state store.
- Forward model-source turns directly through the downstream WebSocket.
- Change HTTP source-selection precedence.

## Decisions

### Store the exact effective selector with the completed anchor

The continuity record will store the selector used for source ownership checks:
the pre-normalization `raw_source_model` when present, otherwise the normalized
request model. The completed response id, input count, fingerprint, pending tool
metadata, and selector are committed together and cleared together.

Using only the normalized model would miss alias-only source transitions. Using
only the raw client value would ignore API-key model enforcement. The existing
`raw_source_model` value already incorporates enforcement before preserving an
alias, so it is the shared HTTP/WebSocket routing selector.

### Refuse implicit anchoring when the selector differs or is unknown

Session-anchor injection requires an exact selector match. A mismatch leaves the
client payload untouched. An older or incomplete in-memory record without a
selector also remains unanchored; a full replay is safer than guessing that
opaque previous-response state is portable.

This is deliberately applied before previous-response ownership resolution. A
model-switched source turn therefore has no proxy-created owner to veto its
configured source route, and the existing WebSocket guard emits
`model_source_requires_http_transport` before upstream selection or send.

### Keep explicit client continuity owner-bound

If the incoming request already contains `previous_response_id`, the existing
recorded-owner policy remains authoritative. This change does not silently drop
client-declared hard continuity or claim that a delta is a complete replay.

## Risks / Trade-offs

- [A harmless alias change causes a full replay] -> Correctness wins over one
  turn of continuity compression; later same-selector turns can establish a new
  anchor.
- [A model-switched replay is too large] -> Existing request-size and context
  admission rules remain authoritative; the proxy does not replace it with a
  context-free delta.
- [An unknown legacy selector cannot be matched] -> Do not inject the anchor.
  Direct-WebSocket continuity is process-local, so deployment naturally starts
  with empty records.

## Migration Plan

No persistent data migration is required. Deploy the application change; new
completed turns populate the selector field. Rollback restores selector-agnostic
anchor injection.
