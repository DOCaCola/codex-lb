## Decision
Remove the lower-bound symbol from the shared monetary formatter, not from cost
classification or aggregation. Retain Unknown, No usage and explicit zero states,
existing detailed coverage descriptions/tooltips and incomplete-comparison guards.
Use the dashboard's existing daily/hourly estimate description for known cost;
unknown/empty estimates use neutral API-equivalent description text.

## Scope and verification
No backend, billing or reservation changes. Monetary consumers share one
formatter, so reports, accounts, conversations and API-key totals stay consistent.
The non-monetary weekly burn-rate symbol remains unchanged. Regression tests
cover complete, mixed, all-unknown, free and empty cost states and dashboard text.
