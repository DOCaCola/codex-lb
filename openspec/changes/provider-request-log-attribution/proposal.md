# Provider request-log attribution

## Why
Provider requests persist source identity but appear Unassigned and cannot be selected in account filters.

## What Changes
Resolve provider names in log responses and account options, use namespaced source filter values, preserve privacy and deleted-source identity, and show attribution in request details.

## Capabilities
### New Capabilities
- `provider-request-log-attribution`: provider identity across request log presentation and filters.

## Impact
Request-log reads and dashboard only. No storage migration or routing changes.
