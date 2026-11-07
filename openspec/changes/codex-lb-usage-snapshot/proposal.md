# Report Quota Pools to Desktop Integrations

## Why

The Codex desktop usage button shows the signed-in ChatGPT account's limits. A desktop routed through codex-lb draws
on codex-lb's pools instead: the ChatGPT accounts, Claude, Antigravity and OpenRouter. The button therefore reports a
quota that may not serve the open thread at all. A CodexDC tweak can show the pools, but it needs one document that
states each pool's remaining quota, its outlook and the models it serves, without probing providers on every poll.

## What Changes

- `GET <base_url>/codex-lb/usage?since=<start of the client's day>` returns the pools available to the requesting key
  under both `/backend-api/codex` and `/v1`. Each pool lists its models, account readiness, quota windows with their
  refill time, and for weekly windows the dashboard pace's outlook: when recent burn spends the pool before relief and
  how much the next reset returns. OpenRouter reports prepaid credits. The document adds the key's request count and
  estimated cost since `since`.
- The snapshot reads stored quota readings and request logs only. It never refreshes usage upstream, unlike
  `/api/codex/usage`, so clients may poll it.
- The capability document lists a `usage` capability with every model a pool serves, so a client can tell a thread's
  pool from its model. Both are withheld when the operator hides upstream quota from API-key clients.

## Impact

- Specs: modified `client-capability-discovery`.
- Code: `app/modules/proxy/usage_snapshot.py`, `app/modules/proxy/api.py`, `app/modules/proxy/schemas.py`,
  `app/modules/claude/client_usage.py` (structured pool summary shared with the rate-limit headers) and
  `app/modules/dashboard/service.py` (weekly pace for a key's accounts and sources).

