# Investigation — 2026-10-28

Production DOCa Claude was reauth_required with expired credentials and last
observed Max 5x metadata. The operator reports resubscribing as Pro on the same
account. Rejected fresh credentials/profile are not retained, so the historical
attempt cannot establish which identity component differed. The stored account
UUID plus the combined account/organization fingerprint is sufficient to classify
the next attempt without another provider request or exposing identity values.

References inspected (source, not live qualification):
- OpenCodex 88aaa7545, src/oauth/anthropic-identity.ts: authenticated account UUID
  matching; no organization equality in import matching.
- OmniRoute 8a8c64ee3, src/lib/oauth/connectionPersistence.ts: automatic matching
  distinguishes organizations; an explicit connection ID takes precedence.
- CLIProxyAPI ad8bdd3f, internal/auth/claude/filename.go: organization-hashed
  credential identity separates organizations on the same email/account.
- Sub2API 0a2a29b32, backend/internal/handler/admin/account_handler.go:
  ApplyOAuthCredentials replaces credentials on the selected record and invalidates
  token cache, preserving account configuration.

These implementations do not establish that Max-to-Pro changes an organization ID.
Our translated search envelopes carry source ID/model, and native resource origins
carry source ID, without organization identity. Relaxing reconnect without changing
that ownership model could treat old organization-owned resources as current.
This change therefore adds diagnostics rather than silently transferring ownership.
Signed thinking already has separate cross-account portability handling; it should
not be blanket-deleted as part of a future organization transition.
