## Why

RFC 6749 section 6 makes the refresh token in a refresh response optional: when
the server issues none, the client keeps using the current one. Our OpenAI
refresh rejected such a response as "Refresh response missing tokens", and the
Claude refresh failed validation and recorded the outcome as uncertain, which
requires signing in again. Either way a healthy account could stop refreshing
until an operator reauthenticated it.

The Codex client keeps the stored refresh token when the field is absent
(`codex-rs/login/src/auth/manager.rs`, `RefreshResponse.refresh_token:
Option<String>`), and CLIProxyAPI PR #7629 does the same for its Claude and
Codex credentials. Our Antigravity refresh already behaves this way.

## What Changes

- OpenAI refresh: a response without `refresh_token` keeps the refresh token
  that was sent. The access and ID tokens remain required.
- Claude refresh: a response without `refresh_token` keeps the current refresh
  token. The authorization-code exchange still requires one.
- A rotated refresh token is applied as before.

## Impact

- `app/core/auth/refresh.py`, `app/modules/claude/schemas.py`,
  `app/modules/claude/client.py`.
- Tests: `tests/unit/test_model_refresh_scheduler.py`,
  `tests/unit/test_claude_credentials.py`.
