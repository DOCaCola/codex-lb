## Why

A refresh rejected by the OAuth endpoint is classified by its error code alone. A 401 whose code is not in the
permanent set (missing, or for example `token_revoked`) is treated as transient, so every refresh attempt sends the
dead refresh token again and the account never reaches `reauth_required`, the state that keeps it routable on its
stored access token until expiry and tells the operator to sign in again.

The Codex client treats any 401 from the refresh endpoint as a permanent failure that requires signing in again,
whatever its code (`codex-rs/login/src/auth/manager.rs`). CLIProxyAPI (514d09f) made the same change, together with
a code list from its provider-generic table; following the endpoint's own client covers those codes without
guessing at them.

## What Changes

- A refresh rejected with HTTP 401 is permanent. Unless its code is already a permanent failure code, it carries
  `refresh_unauthorized` and marks the account `reauth_required`.

## Impact

- Affected specs: `usage-refresh-policy`
- Affected code: `app/core/auth/refresh.py`, `app/core/balancer/logic.py`
