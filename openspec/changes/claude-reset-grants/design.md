## Decisions
Implement cedar_ember only, using existing management headers and runtime version.
Read usage?cedar_ember=1&skip_spend=1; derive organization from authenticated profile.
POST reset_rate_limits with program, grant_id and operation UUID request_id.
Validate eligibility, usable_now, expiry, pause, remaining count and at_limit before
a new operation. No automatic claim or failover to another account.

SQL journal persists intent before network I/O. Bind stable authenticated identity,
grant and operation ID; store organization only as an encrypted claim target or
resolve it afresh from verified profile. Serialize account operations using an
account row update transaction; do not hold locks over network requests. Lease
90 seconds, timeout 25 seconds, same-ID retry window 10 minutes matching inspected
OpenCodex/Claude Code evidence. Unknown stays visible after expiry; no automatic
fresh-ID retry. An expired uncertain attempt requires explicit risk acknowledgement
and a fresh spend gate for a new operation. Terminal results replay without POST.
Persist cleared scopes and result before reporting; first settlement wins.
Do not silently discard unresolved operations when credentials rotate or reconnect.

Add per-window refusal provenance inside the existing cooldown row using a typed
JSON collection. Legacy rows become unknown restrictions, which expire normally.
Selection uses the aggregate deadline. Serialize refusal updates and reset
settlement with the account row. Reset barriers live per cleared window in account
state. Capture physical attempt start for refusals as already done for headers;
older evidence for cleared windows cannot restore cleared restrictions.
Settlement uses the original durable intent timestamp, never a retry timestamp:
an idempotent retry may return the original reset result. It removes only
attributable pre-intent evidence for returned cleared
windows; preserve unknown/entitlement/auth/newer restrictions. Poll/header views
ignore evidence predating the barrier. Do not fabricate zero usage. Fresh polling
after settlement is separate from the durable spend result.

UI: account-details reset dialog, load grants explicitly, show remaining/expiry/
cleared windows, confirm spend, persist pending operation display across reload,
same-ID retry or explicit new-spend risk acknowledgement after expiry. No new
navigation or account section.

References inspected: OpenCodex 3cc34e118192 PR5632 and its journal/audit; OmniRoute
a58000c7685f PR13074 (different program) and unmerged PR14728. Adapt protocol and
safety lessons, not source. GET-only live reports do not qualify redemption here.
