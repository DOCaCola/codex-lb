## Why
Native TPS divided output tokens by `latency_ms - latency_first_token_ms`. `latency_ms` closes when the request log is written, after settlement, usage reservation finalisation and downstream delivery. That tail is not generation time, so native TPS was understated, most visibly on short responses and under database load. The upstream terminal event (`response.completed` or its failure equivalent) is already timed on the WebSocket and HTTP stream paths but was not stored.

## What Changes
- New nullable column `request_logs.latency_upstream_terminal_ms`, measured from the same attempt anchor as `latency_ms` and `latency_first_token_ms`.
- The WebSocket and HTTP stream paths persist the upstream-terminal latency they already measure. Model-source dispatch persists its upstream-reported generation end, which is where its `latency_ms` already ends.
- TPS uses `latency_upstream_terminal_ms - latency_first_token_ms`. Rows written before this change keep `latency_ms` as their only recorded end.
- The request-log API exposes the new field, and the dashboard uses it for per-request generation speed.

## Impact
- Spec: `proxy-runtime-observability`.
- Code: `app/db/models.py`, a new Alembic revision, `app/core/usage/throughput.py`, proxy request-log writers, request-log schema and mapper, dashboard generation-speed helper.
- Migration adds one nullable column; no backfill.
