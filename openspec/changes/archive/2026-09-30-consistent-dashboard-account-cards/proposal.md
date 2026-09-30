# Why

Provider dashboard cards share only their outer border, while independently defining headers, spacing and footers. Codex also has a different grid wrapper. This causes mismatched heights and action placement even within one row.

# What Changes

- Use one shared card anatomy for identity, status, provider content and actions.
- Give every provider the same grid wrapper and content-driven equal heights in multi-column layouts.
- Align card action footers at the bottom and use consistent two-column card quota presentation, including mobile.
- Preserve provider units, unknown/stale states, privacy and all existing actions.

# Capabilities

## Modified Capabilities

- `frontend-architecture`: replace the obsolete fixed-row viewport contract with shared provider card layout and intrinsic grid sizing.

# Impact

Frontend account surfaces, Codex/Claude/OpenRouter card presenters, dashboard grid and regression tests. No API, routing, configuration, dependency or migration change.
