# Context

The comparison chart uses AreaChart for hourly values and LineChart for cumulative totals. A shared hourly stack ID currently adds the series vertically.

# Goals / Non-Goals

- Goal: show every hourly series at its own value on a shared zero baseline.
- Non-goals: change data aggregation, Other grouping, metric controls or cumulative totals.

# Decisions

Remove the stack ID without replacing the existing chart or styling. Keep translucent fills and distinct strokes so overlapping areas remain comparable. Regression tests inspect the chart-series contract for both metrics; browser verification retains all four modes and mobile coverage.

# Risks / Trade-offs

Areas can overlap, but the colored strokes, translucent fills and interactive legend remain available to distinguish keys. The vertical maximum is an individual series maximum, not the hourly total across keys.

# Migration Plan

No migration or configuration change. Rebuild the frontend normally.
