# Proposal

## Why

Successful control requests appear as empty model generations because the request log does not retain their operation. Operators need readable labels without adding a table column or changing accounting semantics.

## What Changes

- Persist server-classified ingress operations separately from workload kind.
- Render operation and workload labels in the existing Warmup area beneath Model.
- Preserve classification across streaming, detached persistence, and bridge reuse; retain unknown historical state.
- Accept the existing count-token workload kind in the dashboard contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `provider-request-log-attribution`: request operation attribution and presentation.

## Impact

One nullable request-log column, ingress context, persistence/API schemas, bridge turn snapshots, internal workload producers and the shared request table. No new column in the dashboard, external calls, changed routing or pricing.
