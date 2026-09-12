# Isolate replay history and verify HTTP budgets

## Why
Replay must retain independent pre-normalization history. Upstream bridge tests still expect WebSocket size rejection and destructive slimming, bypassing the fork's actual transport adapter.

## What Changes
- Snapshot complete replay input before normalization, after retained-history expansion.
- Verify HTTP budget rejection after payload expansion without imposing the WebSocket ceiling on HTTP.
- Exercise real per-turn transport selection with mocked network endpoints and preserve independent dump diagnostics tests.

## Impact
Responses replay ownership and regression coverage. No configuration or production changes.
