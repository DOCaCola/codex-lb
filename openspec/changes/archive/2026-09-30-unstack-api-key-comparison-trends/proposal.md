# Why

Stacking hourly usage makes a key's vertical position depend on other keys. Independent areas let operators compare individual hourly costs and tokens directly.

# What Changes

- Render hourly comparison series as independent, unstacked areas sharing a zero baseline.
- Retain cumulative lines, ranking, Other aggregation, coverage and legend behavior.
- Add regression coverage for both hourly metrics.

# Capabilities

## Modified Capabilities

- `api-keys`: change the comparison panel's hourly presentation.

# Impact

Frontend chart and tests only; no backend, configuration, migration or dependency changes.
