# Report Pool Usage to Codex Clients

## Why

Codex clients learn their usage from three places, and none of them shows the pool codex-lb actually routes across:

- WebSocket turns (every production Mac and Windows client) carry upstream `codex.rate_limits` events, which codex-lb
  forwards verbatim. They describe the one account that served the turn, so the desktop app's usage display and the
  client's warning thresholds follow whichever account was picked, e.g. a burn-first Plus account at 100%.
- HTTP turns carry `x-codex-*` headers that codex-lb already replaces with a pool summary, but that summary averages
  each window only over accounts reporting it. Pro accounts currently report no 5h window, so the pooled 5h figure is
  the Plus account alone: 100% used while both Pro accounts can serve without a 5h limit.
- `/status` reads the usage endpoint at `chatgpt_base_url`, which clients currently point at chatgpt.com.

Turns served by Claude get the OpenAI pool's numbers on HTTP, so an exhausted Codex pool tells a Claude turn it is at
100% and the client offers a switch to Luna, which cannot serve. The pools cannot substitute for each other, so a
combined figure would be meaningless.

Frozen811/codex-lb (`0170f487d`) rewrites `codex.rate_limits` to a pool snapshot; CLIProxyAPI drops the event;
sub2api and opencodex expose the selected account. Upstream codex-lb has no issue or PR.

## What Changes

- **Pool semantics.** Client-facing pool usage treats an account without a 5h window as unconstrained in that window
  while its weekly quota lasts, counts an account exhausted on any window as fully used in every window, and reports as
  reset time the earliest reset of an account that has usage in that window.
- **Per-provider stream snapshots.** On native Codex routes, every `codex.rate_limits` event and every set of
  `x-codex-*` headers describes the pool of the provider that served the turn: the OpenAI pool for OpenAI accounts,
  the Claude pool (plan-weighted, using the weekly window that applies to the served model) for Claude accounts, and
  nothing for OpenRouter and OpenAI-compatible sources. Upstream events are replaced, never merged; additional limit
  families are replaced by their pool aggregate or dropped when the pool has none. Live usage ingestion keeps reading
  the raw upstream values.
- **Usage endpoint.** `/api/codex/usage` for ChatGPT callers reports the OpenAI pool with the same semantics as its
  `codex` limit and adds the Claude pool as an additional limit, so `/status` lists both.
- `hide_upstream_quota_from_api_keys` suppresses the rewritten events exactly as it suppresses the headers.

## Non-goals

- Moving `chatgpt_base_url` to the clients' top level. The client also derives ChatGPT apps, plugins, feedback,
  analytics, cloud configuration and workspace routing from it, none of which codex-lb serves; that needs a separate
  pass-through decision.
- Dashboard, API-key pooled-credit and `/v1/usage` summaries, which share the averaging helper but are not changed here.

## Capabilities

### New Capabilities

- `client-usage-reporting`: what usage codex-lb reports to Codex clients, and from which pool.

### Modified Capabilities

- `responses-api-compat`: native routes retain vendor events, except that `codex.rate_limits` is rewritten.

## Impact

- `app/core/usage/__init__.py`: client pool summary alongside `summarize_usage_window`.
- `app/modules/proxy/_service/rate_limit.py`, `app/modules/proxy/helpers.py`: headers and usage payload built from
  the client pool summary, cached per provider.
- New `app/modules/proxy/rate_limit_events.py`: projection of a `codex.rate_limits` event onto a pool snapshot.
- Forwarding points: `app/modules/proxy/_service/websocket/mixin.py`, `app/modules/proxy/_service/http_bridge/upstream_events.py`,
  `app/core/clients/proxy.py` (native SSE), `app/modules/proxy/api.py` (header selection, `/api/codex/usage`).
- Claude adapter turns: `app/modules/claude/` emits the Claude pool snapshot; Claude pool summary built from
  `claude/quota.py` windows and the plan units in `dashboard/claude_pace.py`.
