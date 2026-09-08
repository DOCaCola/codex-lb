## Why
Native HTTP streams can deliver tool calls only in output_item.done with an empty terminal output. Retaining only that terminal snapshot loses the calls needed by incremental tool results.

## What Changes
- Reconstruct retained HTTP output from indexed completed stream items.
- Preserve authoritative non-empty terminal output and bounded, fail-closed collection.

## Impact
HTTP fallback replay and its regression coverage; no client or deployment settings change.
