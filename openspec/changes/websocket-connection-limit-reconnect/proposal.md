## Why
OpenAI closes a Responses WebSocket after 60 minutes with `websocket_connection_limit_reached`. Codex treats that frame as retryable, opens a new connection and resends the turn, so the turn succeeds. codex-lb still records the closed connection as an error, which inflates error counts and error rates and clutters the request log.

## What Changes
New request-log rows for this upstream terminal are stored as `cancelled`, so the existing error, rollup, top-error and fleet accounting already excludes them. The Request Logs surface exposes them with their own public status, `reconnect`, which has a filter option and an informational badge. Ordinary cancellations keep the status `cancelled`. Historical rows are not backfilled, account health is unchanged because the code was never penalized, and `previous_response_not_found` stays an error.

## Capabilities
### Modified Capabilities
- `usage-error-metrics`: connection-limit terminals are non-error terminals and are shown as reconnects.

## Impact
WebSocket request-log finalization, request-log status mapping, filtering and options, the dashboard status badge and locales, and tests. There is no schema change and no change to API-key settlement or account selection.
