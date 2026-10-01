# Proposal

## Why

Provider identity should be recognizable beside account names across the dashboard
and Accounts page. Technical model IDs make request logs harder to scan.

## What Changes

- Add local, text-free monochrome SVG provider marks with documented official sources.
- Reuse shared logo/name presentation across dashboard cards/lists/logs and account lists/details.
- Display readable model names in request logs; retain exact IDs in native hover tooltips.
- Preserve account privacy, actions, model filters and uncommitted work.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-architecture`: provider account identity and readable log model labels.

## Impact

Frontend assets, shared presentation components, model-label formatting, tests and
OpenSpec. No database migration, provider calls or production deployment.
