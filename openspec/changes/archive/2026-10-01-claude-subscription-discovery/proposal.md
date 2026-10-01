# Claude subscription discovery

## Why
Claude accounts currently discard imported subscription metadata and show no plan
level. Operators need automatically detected Free, Pro, Max and Max multiplier
labels without inferring entitlement or capacity from quotas.

## What Changes
- Preserve subscriptionType and rateLimitTier from explicit credential imports.
- Refresh authenticated bootstrap metadata using the existing coordinated poller.
- Display detected plan labels in shared account cards, lists and account details.
- Keep unknown plans explicit and last-known metadata visible on lookup failures.
- Snapshot selected Claude plans in request logs and display localized labels.

## Impact
Claude accounts backend/frontend and existing JSON account state. No new database
columns, operator settings, routing weights, billing assumptions or credentials.
