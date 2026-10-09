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

API-key breakdown rows and API trend tooltips also use the existing compact
formatter, matching their stat cards, table cells and account-cost legends.
Coverage counts remain accounting metadata, not text appended to chart values.
API-key lifetime bars and percentages compare the recorded estimated cost for
each positive-cost key against the sum of those same amounts. The short subtitle
states this basis, so these shares do not claim to measure a complete provider
invoice. Incomplete or historical coverage does not hide the chart. Unknown
requests are not assigned invented prices or included as zero-cost bars. Other
coverage-sensitive report comparisons and detailed report coverage are unchanged.
