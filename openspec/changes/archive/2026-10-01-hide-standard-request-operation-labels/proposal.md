# Proposal

## Why

Standard Responses and Messages labels repeat the ordinary request path and add noise to the request table. Special operations and workload labels carry useful distinctions.

## What Changes

- Hide Responses and Messages in the table's secondary model line.
- Preserve Warmup, Prewarm, Compaction and other special labels without an empty secondary line.
- Keep explicit operation labels in details and retained metadata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `provider-request-log-attribution`: compact table presentation for standard operations.

## Impact

Shared frontend request table and label formatter/tests. No backend, API, pricing or migration change.
