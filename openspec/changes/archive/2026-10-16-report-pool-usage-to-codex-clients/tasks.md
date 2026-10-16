# Tasks

## 1. Pool semantics

- [x] 1.1 Add a client pool summary for OpenAI accounts: accounts without a 5h window count at 0% with their plan's
  5h capacity, accounts exhausted on any window count at 100% in every window, reset time is the earliest reset of an
  account with usage in that window.
- [x] 1.2 Add the Claude pool summary for a model: plan-weighted 5h and applicable weekly windows, same exhaustion and
  reset rules.
- [x] 1.3 Build rate-limit headers and the `/api/codex/usage` payload from the client pool summary; add the Claude pool
  as additional limit `claude`.

## 2. Per-provider reporting

- [x] 2.1 Add `project_rate_limit_event`: replace a `codex` event with the serving provider's pool snapshot,
  replace other families with their pool aggregate, return nothing when there is no snapshot or quota is hidden.
- [x] 2.2 Apply the projection at every native forwarding point (WebSocket mixin, HTTP bridge, native SSE) after live
  ingestion has read the raw event.
- [x] 2.3 Select response headers by serving provider: OpenAI pool, Claude pool, or none.
- [x] 2.4 Emit the Claude pool snapshot on Claude-served native turns (event on WebSocket, headers on HTTP).

## 3. Verification

- [x] 3.1 Summary tests: Pro without 5h plus Plus at 100% gives ≈7%; exhausted weekly counts 100% in 5h; idle
  account's reset is not reported.
- [x] 3.2 Projection tests: account values never reach the client; additional family aggregated or dropped; hidden
  quota drops the event; ingestion still sees raw values.
- [x] 3.3 Route tests: OpenAI, Claude and OpenRouter turns over WebSocket and HTTP; `/api/codex/usage` lists both pools.
- [x] 3.4 `openspec validate --strict`, ruff, ty, pytest.
