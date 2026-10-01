## Why

Agent-lb source inspection found useful observability patterns and a practical
Claude billing-first cache regression. Our fork already has conversation views,
so extend those instead of duplicating sessions or archiving more content.

## What Changes

- Recognize billing-first native Claude traffic only under the existing CLI
  software/OAuth checks; preserve its system/cache layout.
- Explain failed routing with safe counts of actual exclusions and known recovery
  timing, using the existing provider selection decisions.
- Report current/previous Claude cache activity from request logs, distinguishing
  missing measurements and avoiding workload-specific health thresholds.
- Extend conversation details with provider-account counts, errors, cache writes,
  measured speed summaries and bounded activity series.

## Scope

No timed account resumption, new transcript retention, inference probes, changed
routing policy, production deployment, or separate dashboard navigation.
