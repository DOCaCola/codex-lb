## Why

After a failed metadata check, Antigravity and Claude set a retry time (one hour
for Antigravity) that also blocked manual checks. When the failure was our own,
such as the Antigravity credit parser rejecting an omitted `creditAmount`, the
account kept showing the old error after the fix was deployed, and "Check limits"
did nothing until the retry time passed.

agent-lb blocks a manual refresh only during a rate-limit backoff; opencodex and
OmniRoute bypass their cache on a forced refresh, and sub2api caches Antigravity
failures for one minute.

## What Changes

- Metadata state records whether its retry time is a provider rate limit (429).
- A manual check skips the retry time after other failures and waits for a rate
  limit. Scheduled checks keep honouring every retry time.
- An Antigravity 429 without a retry hint backs off for the endpoint interval
  instead of none.

## Impact

- Backend: Antigravity and Claude metadata refresh decisions and stored state.
