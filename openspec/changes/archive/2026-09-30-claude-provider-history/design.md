# Design

## Context

See proposal.md. Claude protocol projection already renders plaintext summaries as assistant text. Authentication currently assumes every encrypted reasoning item is a Claude envelope. Source continuation expansion owns the logical history before preparation.

## Goals / Non-Goals

Project history without mutating its retained representation or weakening signed-state authentication. No ciphertext decryption, credential rotation, client history repair, synthetic thinking or inference downgrade.

## Decisions

1. Run an immutable foreign-reasoning projection after expansion, before Claude authentication/account selection. Reuse the same explicit-user/external-task boundary as signed replay.
2. Leave `claude-v1.` items untouched for authentication, including empty-display signed blocks. Unknown/foreign encryption never enters that authenticator. Tampered own-prefix envelopes still fail with a specific code and index.
3. Completed foreign reasoning with readable summary/content becomes ordinary assistant text in original order. Preserve distinct text, avoid mirrored duplicates, and never copy ciphertext or item lookup IDs. Plaintext-only reasoning uses the same projection. No plaintext is synthesized.
4. Reject opaque-only foreign reasoning: silently dropping it would violate the user's preservation requirement. Reject foreign encrypted active reasoning even with a summary, since a display summary does not satisfy an active signed continuation. Complete-history compaction rejects foreign ciphertext even with a summary because the full underlying state cannot be represented. Errors name the input index and suggest the original provider or portable context. Retained data remains usable on its original path.
5. Genuine Claude client/conversation/model/account constraints stay unchanged, including fork scope rejection. Do not treat parent affinity as permission to authenticate parent-scoped state in a child.
6. Log conversion counts only; never log reasoning text, ciphertext, signatures or credentials. Use structured payload-error codes so public HTTP/WebSocket diagnostics preserve the specific reason.

## Reference evidence (2026-09-30)

- OmniRoute issues #6953/#12105, merged PR #12386: foreign thinking poisons subsequent Claude turns; never fabricate signatures. Current source `0b62441dbcc3f86a1844a77558733b806537e688` drops unsigned blocks. Readable text preservation is our deliberate improvement, not a claimed merged reference behavior.
- CLIProxyAPI issue #3663 (September 21 follow-up): empty displayed thinking can be legitimate signed state. PR #5497 is unmerged and proposes a thinking downgrade; do not copy it.
- OpenCodex PR #6217 (merged September 28): live Opus 5.5 off-switch rejection. PR #4769/current replay guard: required opaque-only state must fail explicitly instead of fabricating reasoning. Source `569e3e7dae48bafc54b8a1a7e3a85129befe2d98`.
- Sub2API `42bc7f6cffe24bcb471608e48e66b4a0afa1f882`: only decode its Anthropic envelopes; #5329/tests show invalid Responses blocks poison tool follow-ups.

## Risks / Trade-offs

Encrypted-only histories and complete compaction cannot switch losslessly; explicit refusal is intentional. Historical summaries are portable context, not the original private chain of thought. Mixed genuine Claude envelopes remain independently scoped; this change does not authorize unsafe fork replay. Mock qualification proves transformation and errors, not live OAuth eligibility.

## Migration Plan

No schema or settings changes. Deploy the tested fork through the existing production upgrade.sh; use its retained rollback image if readiness fails.
