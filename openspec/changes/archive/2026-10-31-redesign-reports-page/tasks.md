# Tasks

## 1. API

- [x] 1.1 Introduce `ReportFilters` (account IDs, model-source IDs, API-key IDs, models, user-agent groups) and use it
      across the API, cache key, service, repository, rollup source and speed medians.
- [x] 1.2 Accept repeated `model`, `useragent_group` and `model_source_id` query parameters.
- [x] 1.3 Add `dailyByAccount` and `dailyByModel` with token, request, cost and coverage measures.
- [x] 1.4 List provider accounts in `GET /api/reports/options`, scoped by date and API key.
- [x] 1.5 Return `avgCostPerDay` for every report; remove `percentage` from model and user-agent entries.

## 2. Dashboard

- [x] 2.1 Toolbar card with presets, custom range, comparison window, generation time, refresh, multi-select filters,
      Reset and Sections menu.
- [x] 2.2 Summary cards with neutral deltas and coverage marker.
- [x] 2.3 Daily trend card with metric and split controls.
- [x] 2.4 Breakdown bar lists with cost/requests switch and row filters.
- [x] 2.5 Latency and throughput mini charts.
- [x] 2.6 Daily breakdown table without inner scrolling, totals row, date display preference.
- [x] 2.7 Collapsible Routing diagnostics.
- [x] 2.8 Remove the donut and per-metric chart components; en, ko and zh-CN strings.

## 3. Verification

- [x] 3.1 Backend unit and integration tests for filters, splits, options and averages.
- [x] 3.2 Frontend tests for the page, toolbar, trend, breakdown, table and diagnostics.
- [x] 3.3 Typecheck, lint, `openspec validate --specs --strict`, and a rendered check with production-shaped data.
