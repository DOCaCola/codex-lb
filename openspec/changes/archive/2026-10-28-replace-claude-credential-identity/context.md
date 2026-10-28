# Explicit credential replacement

An operator reported the same browser login after Max 5× → Free → Pro, but the
authenticated account UUID differed from the saved UUID. This establishes an
identity mismatch, not that the subscription transition caused it. No reference
report inspected establishes that causal claim. Do not match by email or silently
accept identity changes.

## Reference evidence (inspected 2026-10-28)

- OpenCodex `88aaa7545`: explicit reauthorization checks account identity and rotates
  login ID; continuity captures credential identity/generation. Its import fix
  `84630c57e` verifies bearer-owned identity.
- Sub2API `0a2a29b32`: dedicated account credential replacement preserves non-auth
  settings, clears auth errors and invalidates cached tokens. PRs
  https://github.com/Wei-Shaw/sub2api/pull/2796 and
  https://github.com/Wei-Shaw/sub2api/pull/7404 document those preservation fixes.
- OmniRoute `8a8c64ee3`: automatic matching is organization-aware, while explicit
  connection replacement targets the selected entry. Discussion
  https://github.com/diegosouzapw/OmniRoute/discussions/15096 describes personal/Team
  collisions with matching email/account UUID.
- CLIProxyAPI `ad8bdd3f`: organization-qualified credential filenames prevent
  accidental personal/Team replacement (issue
  https://github.com/router-for-me/CLIProxyAPI/issues/5709).

## State and race model

Normal reconnect remains strict. Explicit consent authorizes replacement of the
selected logical account; it does not assert that two provider identities are equal.
For example, an operator can replace an expired Max identity with a new Pro login
while retaining the dashboard's DOCa Claude statistics and routing settings.

`AccountState.identity_generation` is the first credential generation belonging to
the current authenticated identity. Rotation within an identity leaves it unchanged.
Replacement advances it atomically with credentials, clears live observations and
affinity, and removes materialized models until discovery runs. Existing state and
encrypted envelopes have generation 1 because replacement was previously forbidden.

Native resource provenance also stores identity generation. Resolution rejects
resources belonging to a previous identity. Rows remain until their normal expiry
because the table also retains refusal markers: those describe previously delivered
output and must survive replacement. Late native provenance writes require the
current identity under the account lock; refusal writes are safe for their original
generation. Refused output cannot become a native resource because keys use separate
namespaces. Completed translated search is projected as readable content; active
search remains nonportable. Thinking follows the existing portability policy.

Prepared requests verify identity before every attempt. A request already in flight
may finish under its old credentials, but cannot establish current native ownership,
quota or cooldowns. Metadata claims and refresh rotation retain their existing
credential-generation fences. Historical accounting remains attached to the logical
account, deliberately spanning explicit replacements.

Validation uses mocked provider traffic only. Live subscription-transition UUID
behavior is not established by these tests.

## Verification

- Claude replay, protocol and account/transport integration selection: 515 passed.
- Final resource/session admission, identity replacement and failover checks: 115 passed.
- Broader Claude unit/auth recovery/reset/search/routing selection: 803 passed;
  its one outdated message assertion was corrected and passes in the final selection.
- Account UI: 31 passed; frontend typecheck and touched-file lint pass.
- SQLite migration to head and schema check pass with no drift; 77 main OpenSpec
  specifications and this change validate strictly.
- Python typecheck still reports the existing list variance error at
  `app/modules/claude/routing.py:105`; no changed-code diagnostic.
