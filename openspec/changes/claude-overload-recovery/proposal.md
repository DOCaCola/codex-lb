## Why
Explicit Claude overload refusals and HTTP200 early SSE overloaded_error currently cannot recover without client retries.

## What Changes
- One same-account overload retry within the existing four-send budget and a ten-second request recovery window.
- Bounded SSE startup inspection before public events or generation.
- Preserve failures after generation and avoid account/provider health penalties.

## Capabilities
### Modified Capabilities
- `claude-accounts`: explicit overload recovery.

## Impact
Claude transport and shared dispatch; no schema/configuration changes.
