# Context

## Purpose

Make the usage a Codex client sees describe the capacity codex-lb can actually route to for that turn. Normative rules
are in `specs/client-usage-reporting/spec.md`.

## Client behaviour (openai/codex, 2026-10-15)

- HTTP/SSE turns: the client parses only response headers (`codex-api/src/sse/responses.rs` `parse_all_rate_limits`).
- WebSocket turns: the client parses `codex.rate_limits` events (`codex-api/src/endpoint/responses_websocket.rs`,
  `rate_limits.rs` `parse_rate_limit_event`), not handshake headers.
- Both feed the turn's token-count event. The app server forwards it as `account/rateLimits/updated`
  (`app-server/src/bespoke_event_handling.rs`), so the desktop app displays the streamed figure.
- The TUI uses streamed snapshots for warnings at 50/75/90/95% (silent at exactly 100%) and for the switch-to-Luna
  prompt at 90% on the `codex` limit (`tui/src/chatwidget/rate_limits.rs`). Its status breakdown comes from the usage
  endpoint. The client never blocks on a reported percentage; it blocks on a `usage_limit_reached` error.
- `/status` and `account/rateLimits/read` call `{chatgpt_base_url}/api/codex/usage` (or `/wham/usage` for
  `/backend-api` bases). `chatgpt_base_url` is read only at the config top level; the production Mac config sets it
  inside `[model_providers.codex-lb]`, where it has no effect. The same base URL drives ChatGPT apps MCP, plugins,
  feedback, analytics, git attribution and workspace routing.

## Production evidence (2026-10-16)

| Account | Plan | 5h | Weekly |
|---|---|---|---|
| Andy Alpha | Pro | no window | 43% |
| Andy Beta | Pro | no window | 9% |
| DOCa Plus | Plus | 100% | 56% |

Current pooled 5h: 100% (Plus only). Under this change: (1500·0 + 1500·0 + 225·100) / 3225 ≈ 7%.

The Mac client is ChatGPT-authenticated with a pool account, so `/api/codex/usage` would accept it.

## Decisions

- **Unconstrained, not missing.** An account that reports no 5h window has no 5h limit; leaving it out of the
  average makes the pool look 5h-limited exactly when it is not. It is weighted with its plan's 5h capacity at 0%.
- **Exhaustion is total.** An account at 100% on any window cannot serve, so it counts as fully used in every window.
- **Reset time.** The earliest reset among accounts with usage in the window is when the pooled figure next drops.
  The previous minimum over all accounts could name an idle account's reset, which changes nothing.
- **Per provider.** The client's single `codex` limit drives warnings and the Luna prompt for the turn in hand, so it
  must describe the pool serving that turn. Sources without subscription windows (OpenRouter, OpenAI-compatible) emit
  nothing; the client keeps its previous snapshot, which cannot trigger a new warning.
- **Claude weekly.** Per account, the weekly figure is the most-used weekly window applicable to the served model
  (`seven_day` plus `seven_day_opus`/`seven_day_sonnet` where they apply), because that is the binding limit.
- **Replace, never merge.** Mixing the account's fields into a pool snapshot would reintroduce the leak. Additional
  families (`limit_id` other than `codex`) get their pool aggregate, which already exists for the usage payload.

## Failure modes

- Pool figures come from the cached summary and can lag live ingestion by up to one usage refresh interval.
- When the pool summary cannot be loaded, the event is dropped and logged; the turn continues.

## Example

A WebSocket turn served by DOCa Plus receives upstream `codex.rate_limits` with primary 100%. The client instead
receives primary ≈ 7% with the Plus 5h reset, and secondary at the capacity-weighted weekly figure. The account's raw
100% is still ingested for routing.

## References

- Frozen811/codex-lb `0170f487d` `app/modules/proxy/rate_limit_events.py` `project_codex_rate_limit_event`.
- CLIProxyAPI `sdk/api/handlers/openai/openai_responses_handlers.go`: drops `codex.rate_limits`.
- sub2api `openai_gateway_passthrough.go`: forwards the selected account's `x-codex-*` headers.
- opencodex `src/server/responses/codex-ws-metadata.ts`: per-account handling.
