## Why
Credit-backed capacity silently keeps an account routable after its quota windows fill, so a ChatGPT account's purchased credits are spent with no way to reserve them. Operators need a per-account opt-out. Separately, an open upstream websocket kept serving its downstream session after its account became unavailable (paused, deleted, deactivated), because websocket reuse never rechecked routing availability. Neither upstream codex-lb nor the Codex CLI offers a credit opt-out (codex-lb #764, #2119 and #1528 only cover usage limits; openai/codex #28382 and #48394 are open feature requests).

## What Changes
- Accounts SHALL have a credit policy: `spend` (default, current behavior) or `never`.
- Under `never`, credits SHALL NOT override quota exhaustion; status is derived from usage and the account becomes unavailable once a window is exhausted. Its credits SHALL NOT count toward pooled credit headers and payloads.
- `PUT /api/accounts/{id}/credit-policy` SHALL update the policy and propagate it to every replica through the routing-availability snapshot.
- A reused upstream websocket SHALL recheck routing availability before each turn; an unavailable account's socket is retired and the turn moves to another account or fails closed.
- The Accounts page SHALL expose the policy as a Credits setting.

## Capabilities
### New Capabilities
### Modified Capabilities
- `usage-refresh-policy`: per-account credit policy.
- `responses-api-compat`: live websocket sessions stop using unavailable accounts.
- `frontend-architecture`: account credit policy control.

## Impact
New `accounts.credit_policy` column and migration, quota/status derivation, load balancer, usage updater, routing-availability cache, websocket reuse path, pooled credit headers, accounts API, Accounts page and translations.
