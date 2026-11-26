## Why

A Claude token refresh ran inside the request that needed it, on that request's database session. When the client disconnected mid-refresh, the request was cancelled together with the refresh. The refresh intent was then never settled, and the account reported uncertain credentials until an operator reauthenticated it, even when Anthropic had answered successfully. The intent was meant to survive only a crash, where the outcome is truly unknown.

Parallel requests on the same account also failed with "refresh in progress" while this process's own refresh was running.

OmniRoute #20789 (Nov 25) fixed the same defect: a dispatched OAuth refresh must complete even when its caller is aborted, because the provider may already have rotated the refresh token. Codex accounts here already refresh in a detached, shared task with their own session (`AuthManager._run_refresh`).

## What Changes

- `ClaudeAuth.snapshot` starts the refresh as a detached task, keyed by account and generation, that claims, refreshes and settles the intent in its own session.
- Callers in the same process share that task; a cancelled caller only stops waiting.
- An intent held by another worker is still never stolen, and a refresh cancelled by shutdown still leaves its intent, so a consumed refresh token is never replayed.

## Impact

- Spec: `claude-accounts`.
- Code: `app/modules/claude/auth.py`.
- No settings, schema or client changes.
