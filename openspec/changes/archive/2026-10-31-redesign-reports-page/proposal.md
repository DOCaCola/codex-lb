## Why

The Reports page hides data and misreads it. The model and user-agent legends scroll behind hidden scrollbars, so rows
such as `gpt-6-luna` are present but invisible; the daily table scrolls inside a short box that cuts off a day and its
last column; the per-account cost breakdown the API already returns is never shown. Smoothed area charts invent peaks
and dips between daily points, the token chart plots billions of input tokens and millions of output tokens on one
scale, and rising spend is coloured as a green improvement. A title, a filter card, a separate refresh row, uneven
summary cards, five full-size charts and a large diagnostics table make the page long without making it clearer.

Filtering is also incomplete: Claude, OpenRouter and other provider accounts cannot be selected because the account
filter only matches Codex account IDs, and model and user-agent filters accept one value each.

## What Changes

- Replace the title, filter card and refresh row with one toolbar card in the Logs-page pattern: range presets with a
  custom range, the readable range and comparison window, the report generation time with refresh, and a second row of
  multi-select Accounts, API keys, Models and User agents filters with Reset and a Sections menu.
- Show five equal summary cards (cost, tokens, requests, active conversations, errors) with one detail line each,
  details in tooltips, and neutral change indicators. Incomplete cost coverage is marked on the card and explained in
  its tooltip.
- Replace the five line charts with one Daily trend card: daily bars for Cost, Input tokens, Output tokens or
  Requests, split by total, account or model. Input splits into cached and uncached, output into visible output and
  reported reasoning.
- Replace both donuts with a Breakdown section of account, model and user-agent bar lists that show every row, switch
  between cost and requests, and apply a filter when a row is activated.
- Show TTFT, TPS and queue wait as three compact straight-line charts of the real daily medians; values far above the
  others are drawn at the top edge with their value instead of setting the scale.
- Show every day and column of the Daily breakdown without an inner scroll area, with a totals row; day labels follow
  the date display preference.
- Fold thread identity and cache locality into a collapsed Routing diagnostics section whose header shows the key
  figures; it loads only while open.
- API: accept repeated `model` and `useragent_group` filters and a repeated `model_source_id` provider-account
  filter; add daily account and model splits; list provider accounts in the options catalog; always return the
  per-day cost average as a known-cost average; drop the unused `percentage` fields.

## Impact

- Affected specs: `reports`, `report-aggregation`, `frontend-architecture`
- Affected code: `app/modules/reports`, `frontend/src/features/reports`, `frontend/src/components/lazy-recharts.ts`,
  translations
