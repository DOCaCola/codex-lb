## Why

A Terms of Service ban from Cloud Code marks the account banned, but recovery then
resent the same request on the next pooled account. Google bans the account that
submitted the content, so every replay submits content it has just rejected from
a fresh account. During the November 2026 ban wave CLIProxyAPI observed one
request walking the pool this way, each attempt ending in another ban
(CLIProxyAPI PR #7636). opencodex now pauses an account on its first ban
(#8826). We already hold the banned account; the replay was the remaining gap.

The client also received a 503, which the Codex client retries, so its retry
loop could start the same cascade on the next account.

## What Changes

- A ban ends the request: the account is still held as banned, but no other
  account is tried.
- The client receives 403 `antigravity_account_banned` with
  `x-should-retry: false`, so no client retry loop resends the content.
- Other 403 refusals keep their current failover behavior.

## Impact

- `app/modules/antigravity/recovery.py`.
- Tests: `tests/unit/test_antigravity_recovery.py`,
  `tests/integration/test_antigravity_accounts.py`.
