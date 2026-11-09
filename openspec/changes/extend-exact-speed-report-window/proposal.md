# Extend exact report speed medians to ninety days

## Why

The reports page omits TTFT, TPS and queue medians for ranges longer than seven
days. Upstream chose that ceiling when its production 7-day reports took 44–53
seconds. Our production volume is far smaller: measured against production on
November 8, 2026, the exact daily median query took 0.4 s for 7 days, 1.8 s for
30 days and 2.5 s for 90 days. The 30- and 90-day presets therefore lose speed
metrics without a cost reason.

## What Changes

- Exact speed medians run for report windows of up to 90 days, the longest
  report preset. Longer custom ranges keep the existing omission notice.
- `speedMetricsAvailable` and `speedMetricsMaxDays` are always part of the
  reports response; the dashboard reads the ceiling from the server.

## Impact

Reports service, reports dashboard schema. A 90-day report adds about 2.5 s of
database work per uncached load at current volume. Request-log retention is off;
enabling it would shorten the raw history that speed medians can read.

Pre-aggregated speed histograms were evaluated and deferred: on production data
they compress raw samples only about 2.7×, return approximate medians, and need
a refold whenever the TPS definition changes.
