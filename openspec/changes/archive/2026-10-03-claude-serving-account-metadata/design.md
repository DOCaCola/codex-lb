## Context
See proposal.md for the observed metadata mismatch and reference revisions.
Credential identity is already authenticated through the profile endpoint and
represented by an account-and-organization fingerprint.

## Decisions
- Persist the profile account UUID alongside that fingerprint rather than infer
  it from client metadata or tokens. Enrollment and reconnect have the profile
  available; existing rows acquire it during credential identity verification.
- Verify the enrolled fingerprint before backfilling the UUID. Bind updates to
  the credential generation so reconnect cannot publish stale identity.
- Project metadata after the credential snapshot and selected-account re-read.
  Both native and translated metadata then match the serving bearer credential.
  Native requests without metadata preserve their original shape.
- Expose a typed extra-usage enabled flag from the retained usage snapshot and
  reuse the existing warning badge styling. This is an operator indication;
  it does not introduce an overage refusal policy.

## Risks / Trade-offs
- The first credential use after migration requires a profile lookup. Provider
  failure rejects that request and leaves the UUID unset for the next attempt;
  no fabricated identity is sent.
- Usage metadata can be retained after a refresh failure, so the badge describes
  the latest known provider state, consistent with existing quota presentation.

## Migration Plan
Apply the nullable UUID column through the normal upgrade. Existing credentials
remain encrypted and unchanged; UUID backfill is authenticated on first use.
The migration supports downgrade by removing only the added column.
