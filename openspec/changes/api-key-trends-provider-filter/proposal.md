## Why

The APIs page "Usage Trend by API Key" chart mixes Codex, Claude and OpenRouter
usage, so operators cannot see how each key uses each provider. The hourly
usage rollup that serves the chart had no provider dimension, so a provider
filter could not be applied to folded history.

## What Changes

- Fold the request's model-source kind into `request_usage_hourly_rollups` as
  a key dimension; a migration adds it and re-folds retained raw history.
- `GET /api/api-keys/trends` accepts an optional `provider` filter.
- The comparison chart gains an All / Codex / Claude / OpenRouter control.

## Capabilities

### Modified Capabilities

- `api-keys`: provider-filtered collection trends and chart control.

## Impact

- Backend: hourly rollup model, fold, cost backfill mirror, API-key trend
  reader and endpoint, one migration.
- Frontend: APIs page comparison chart, hook and API client, locales.
- Deployment: the first fold pass after upgrade re-folds retained raw history
  into the hourly rollups (production keeps raw logs back to April).
