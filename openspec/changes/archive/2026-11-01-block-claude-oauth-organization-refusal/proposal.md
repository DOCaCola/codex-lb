## Why

When a Claude subscription lapses, Anthropic answers every inference request with
403 `permission_error` "OAuth authentication is currently not allowed for this
organization." codex-lb passed this through as an ordinary error and kept the account
in rotation. On 2026-11-01 a Max subscription ended and 9 conversations sent 97
requests in 4.5 minutes to Anthropic before the account was renewed as Pro.
agent-lb persists this exact refusal as a subscription usability block, fails over,
and clears it after a successful usage refresh; opencodex classifies the same whole
message as an account-scoped refusal.

## What Changes

- The exact organization OAuth refusal (whole message, `permission_error`, 403)
  records a block on the account's current credential generation and fails over
  within the existing request send budget. Other 403 responses keep their behavior.
- A blocked account is ineligible for routing, including sticky selection. A pool
  of only blocked accounts fails locally with 400 `claude_subscription_inactive`
  and sends nothing upstream; the request that triggered the block still reports
  Anthropic's refusal.
- A usage or subscription refresh requested after the block and answered
  successfully clears it, as does a reconnect. A still-lapsed subscription is
  re-blocked by its next request.
- The Providers page shows the account as deactivated with "Subscription inactive".

## Impact

- Backend: `app/modules/claude/failover.py`, `routing.py`, `schemas.py`,
  `service.py`, `app/modules/proxy/api.py`, `app/core/routing_diagnostics.py`.
- Frontend: Claude account schema, status and provider notice; en/ko/zh-CN strings.
- No database migration: the block lives in the account state JSON.
