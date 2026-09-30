# Proposal

## Why

The APIs overview shows lifetime shares and individual key trends, but cannot compare recent usage across keys. A combined seven-day chart makes changes in spend and token consumption visible without opening each key.

## What Changes

- Add a dashboard-authorized collection trend endpoint with a shared hourly seven-day window, preserving cost coverage and retained usage for deleted keys.
- Add a full-width overview chart between summary statistics and lifetime breakdowns.
- Offer cost/token and hourly/cumulative controls, a top-five plus Other comparison, and an interactive legend.
- Reuse the existing chart, card, toggle, and responsive styling.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-keys`: collection trend data and dashboard comparison presentation.

## Impact

API-key repository, service, dashboard schemas and routes; APIs frontend queries, chart, translations and tests. No database migration, configuration setting or new dependency.
