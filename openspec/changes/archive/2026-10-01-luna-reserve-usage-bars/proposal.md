# Proposal

## Why

Luna Reserve has separately reported usage windows, but operators cannot see them in account details. Reuse the additional-quota bar layout rather than introduce a history chart or change routing.

## What Changes

- Opt account usage refresh into the upstream Reserve-capable usage query.
- Persist the latest account-bound Reserve observation independently of routing telemetry.
- Display reported Reserve windows, reset countdowns and unknown/unavailable states in existing additional-quota cards.
- Keep ordinary quota, Spark behavior and model admission unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `account-quota-presentation`: Reserve telemetry in account-detail quota bars.

## Impact

Usage client/parser/updater, one nullable account snapshot migration, account API summaries, account usage panel and regression tests. No deployment, model catalog expansion or entitlement grant.
