# Design

## Context

A production Opus-to-Sol switch replayed a reasoning item with `resp_msg_…` ID, empty summary and `claude-v1.` encrypted content. IDs and provider-specific state are separate incompatibilities: changing the prefix alone does not make the blob usable.

## Decisions

1. Project only at native subscription dispatch after retained history expansion, before continuity trimming, reservation or account selection where feasible. Keep logical retained input unchanged.
2. Reuse Claude envelope authentication; do not require the destination to match the originating Claude model/account when extracting portable thinking. Scope remains client and conversation bound, using the same header resolution as source continuation.
3. Convert readable `thinking` into `summary_text`, preserving existing summaries and distinct plaintext reasoning. Remove its foreign encryption and ID rather than renaming them. Native normalization empties reasoning.content and strips output status.
4. Redacted thinking cannot be decoded into text. Claude server search contains signed/provider-owned resources. Reject these with `nonportable_provider_history` and a precise input path before dispatch. Do not fabricate search calls, signatures, or claim that opaque data was preserved at the destination. Original retained data remains untouched and usable with Claude.
5. Shared native sanitation validates known item-type ID prefixes independently of store mode and encrypted-content presence. Stateless lookup removal remains unchanged for native blob-bearing IDs and item_reference. Unprojected Claude envelopes fail closed at the low-level boundary.
6. No inference retry, account-health change, new retention store, configuration setting or client patch.

## Reference evidence (source/test inspection, 2026-09-30)

- OpenCodex `569e3e7dae48bafc54b8a1a7e3a85129befe2d98`: request-strips.ts validates type prefixes; reasoning.ts removes proxy ocxr1 envelopes; core-replay.ts binds encrypted state to route provenance.
- CLIProxyAPI `a270e7b9e57aaecd8f82555f44c2108518ad2330`: openai_responses_signature.go and tests validate native blob shape, remove orphan IDs and promote plaintext into summaries.
- Sub2API `42bc7f6cffe24bcb471608e48e66b4a0afa1f882`: openai_codex_transform.go strips reasoning lookup IDs; encrypted-content lineage handles rejected blobs reactively.
- OmniRoute `fc5e2bccd4f70fecf5aab94dfb8136c74ab5a21b`: reasoningInputPolicy.ts governs transport compatibility; native rejection classification is not proof of exact foreign-envelope prevention.

These are behavioral references, not copied implementations or live OAuth qualification. Unlike blanket foreign-blob stripping, the projection preserves recoverable text and rejects unrecoverable state.

## Verification

Test production-shaped empty-summary envelopes, plaintext and native encrypted replay, mixed tool cycles, tampering/cross-scope rejection, source-path isolation, retained previous-response expansion, HTTP/WebSocket serialization and native compaction. Inspect output and ensure logical input is unchanged.
