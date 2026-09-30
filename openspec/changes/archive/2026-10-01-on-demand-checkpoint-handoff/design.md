# Design

## Context

See proposal.md. Source history preparation already materializes scoped readable
checkpoint snapshots before projection. Native compact and WS finalizers provide
the successful original account and model after usage settlement. Native streaming
provides metering, cancellation-safe cleanup, account admission and health handling.

## Goals / Non-Goals

**Goals:** generate a summary only for unreadable native checkpoints on a source
route; preserve scope, owner pins, accounting and original history on failure.

**Non-Goals:** decoding OpenAI ciphertext locally, guessing legacy ownership,
replaying hosted resources across providers, a client fork or production rollout.

## Decisions

- Native completion records model/account/type/id under ciphertext digest + API
  key + conversation. It does not copy compact input, images or ciphertext.
  A newly observed native compact can establish provenance even if older inputs
  are opaque; the native backend has successfully processed them.
- Existing readable snapshots are still usable until their existing expiry. New
  normal compactions retain only provenance. On-demand summaries use bounded
  private storage, 30-day retention, 512 KiB per entry, 64 MiB total; provenance
  uses 30-day retention, 10k entries and 16 MiB total. No claim of lifetime recovery.
- Handoff asks the recorded native account/model to summarize just its exact
  checkpoint, without tools or truncation. Surrounding visible history stays
  ordered and unchanged. The summary prompt requests task decisions, constraints,
  evidence and unresolved work, not transport debris. Incomplete/refused/empty
  summaries do not become portable context.
- Native streaming gains an internal hard account pin. Handoff uses the normal
  reservation and request-log lifecycle, a separate request ID, no HTTP bridge,
  no client continuation handles or mutable client affinity headers. Access
  restrictions are rechecked on cache hits and generation.
- A private SQLite claim serializes generation across workers. Concurrent requests
  return an explicit retryable busy error rather than making duplicate calls.
  Claims have a deadline beyond the bounded generation budget; cancellation and
  errors release them. Successful summaries are published before destination dispatch.
- No source call receives checkpoint ciphertext. Snapshot miss, then summary-cache
  hit, then verified native handoff is the only recovery order. No provenance means
  an indexed failure, not a guessed account or placeholder.

## Risks / Trade-offs

- Summarization is lossy and billed additional work, authorized by this feature.
  Logs and usage reservations account for the native request independently, using
  existing tracked detached persistence instead of changing normal response latency.
- Reference inspection on 2026-09-30/10-01: OpenCodex cae9b553 uses routed ocx1
  summaries but placeholders for native blobs; Sub2API 42bc7f6c and CLIProxyAPI
  97f244b8 omit unsupported checkpoints; OmniRoute fc5e2bcc rejects them on its
  normal translator. This is a new recovery path, not inherited live qualification.
- Original owner/model unavailable or native ciphertext rejection -> explicit
  failure without source dispatch or cross-account generation.
- Provenance/summary expiry, eviction or disk failure -> explicit recovery error.
  No unlimited archive and no silent shortened-history retry.

## Migration Plan

No primary database migration. New private directories are created lazily. A
rollback ignores the new metadata/cache; native protocol behavior is unchanged.
