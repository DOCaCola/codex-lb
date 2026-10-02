# Why

The dashboard request log refreshes in place. Rows that arrive with a refresh look identical to rows already on screen, so an operator watching the log cannot tell at a glance which entries just appeared.

# What Changes

- Rows that arrive through a refresh of the request log, while its filters and page stay the same, get a tinted background that fades to the normal row background over a few seconds.
- The initial load, filter, search, page-size and page changes, and placeholder data shown while a new filter loads establish a new baseline and highlight nothing.
- Only the first page highlights arrivals; later pages only shift as newer rows push entries along.

# Capabilities

## Modified Capabilities

- `frontend-architecture`: add live-arrival highlighting to the dashboard request log.

# Impact

Dashboard request-log table, a frontend hook, global CSS and frontend tests. No API, backend, configuration, dependency or migration change.
