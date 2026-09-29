# Proposal

## Why

Claude model selection currently substitutes operator-entered token budgets for discovered capabilities, and its account views diverge from the established Codex layout. Claude also omits the per-account routing policy supported by the shared scheduler.

## What Changes

- Discover model token limits and supplement absent fields with explicitly maintained model metadata.
- **BREAKING** Remove manual Claude context/output overrides from selection API and UI; migrate existing selections and projected models.
- Reuse Codex quota, routing and account information components across Claude dashboard/list/detail views, preserving unknown/stale quota information.
- Add normal/burn-first/preserve policies within the Claude pool, preserving hard ownership and eligible affinity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `claude-accounts`: Automatic token capabilities, consistent account views and per-account routing policy.

## Impact

Claude catalog, schemas, projection, scheduler, migration, dashboard account components and regression tests. No production deployment or credential mutation is part of this change.
