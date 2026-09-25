# Implementation checkpoint — 2026-09-25

This change remains in progress, not deployable Claude inference support.

## Implemented and locally verified

- Encrypted import/PKCE persistence, single-use and expiry boundaries, explicit
  inference-scope validation and credential redaction.
- A single additive Alembic head; fresh upgrade, schema-drift check, downgrade
  to the OpenRouter parent, then re-upgrade on an isolated SQLite database.
- Durable token refresh intent/generation, cross-session exclusion, successful
  rotation/restart, definitive transient rejection/backoff/retry, and uncertain
  consumption retention. Each grant must have one refresh consumer; importing a
  Claude Code grant does not coordinate with the external CLI. Operators must
  acknowledge this explicitly.
- Shared CLI version discovery (24 hours), immutable snapshots, pin/rollback
  via dashboard-authenticated `GET/PATCH /api/claude-accounts/version`, retained
  version on discovery failures, separate checked/changed timestamps, conditional
  requests and stale-feed downgrade prevention. A null pin resumes discovery.
- Leader-gated metadata scheduler, immediate first tick, no Claude discovery when
  there are no enabled healthy accounts, separate sessions per account and safe
  failure isolation. Test lifespans stub the new scheduler builder.
- A pure request-profile/projection boundary with independent CLI/SDK versions,
  management/Messages/count-token headers, scoped session identity independent of
  credentials, fresh request IDs and native newer-patch recognition. Recognition
  is not an authentication boundary or a global profile-learning mechanism.
- Modern instruction relocation and legacy user reminders preserve original block
  text/cache markers and existing tool/signed-thinking turns. The original
  logical request is never mutated. Unknown placement capabilities and server-tool
  history requiring a layout rewrite fail explicitly. Ordinary tools named
  `advisor` are not treated as server artifacts.

## Still required before completion

Follow-up after foundation commit: account responses now expose derived quota
windows and per-selected-model blocking status. Monitoring becomes stale after
five minutes or a refresh failure; an observed exhausted window remains blocking
until its known reset. Passing reset changes freshness to unknown, not zero usage.
Missing/null windows do not establish denied entitlement. Unknown provider windows
remain in the original snapshot without an invented model association. Pagination,
cursor/duplicate rejection, selection retention and the dashboard API contract
are covered by local tests. The Claude-specific suite has 55 passing tests; this
does not yet exercise inference pool selection, which remains pending below.

The pool selector and dispatch preparer are now implemented and covered by
two-account database tests: source/model scopes, worker-independent affinity,
paused/auth/refresh/quota exclusions and mandatory continuation ownership.
Preparation validates the request before rotating credentials, snapshots the
profile once, replaces caller authorization, maps only the selected provider
model, and rechecks account eligibility after a potentially slow token refresh.
An operator pause during rotation prevents a prepared inference request. Headers
and request bodies are excluded from the prepared request's diagnostic repr.

The request profile is not yet connected to inference transport. Pool admission,
Messages/count-token routing, Responses HTTP/WS adaptation, stream lifecycle,
opaque-state continuation/compaction, authenticated identity/reauthentication,
and unified frontend remain incomplete. Selected models must not be considered
live inference support from the existence of account-management endpoints.

Only fixture and isolated database verification has been performed. Neither
upstream OAuth acceptance nor included subscription billing has been tested.
No production credentials, production configuration, deployment or live Claude
requests were used. Version discovery updates an advertised version, not SDK
code, executable software or a guarantee that the complete profile still works.

## Profile evidence

Behavior was independently implemented from the source references in AGENTS.md
and the temporary research document, not copied wholesale. CLIProxyAPI's
non-strict instruction preservation, model-specific placement and newer-patch
recognition inform the boundary; Sub2API's stale-version and cache regressions
inform discovery and preservation tests. Full profile parity is not claimed:
private billing signatures, strict instruction deletion, broad text obfuscation
and silent paid fallback are not implemented.
