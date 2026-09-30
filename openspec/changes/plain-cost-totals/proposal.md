## Why
The user finds the recently added greater-than-or-equal prefix on estimated cost totals unhelpful. Keep coverage semantics without inserting mathematical symbols into currency displays.

## What Changes
Remove the ≥ prefix from formatted monetary totals. Restore the dashboard's Est. API Cost heading and ordinary estimated daily/hourly average description without coverage counts. Use compact monetary labels for API-key lifetime breakdown rows and API cost-trend tooltips, without inline coverage-count strings. Restore API-key bars and percentages relative to recorded estimated cost even with incomplete coverage, and identify that basis in the subtitle. Preserve unknown-versus-free handling and detailed coverage descriptions elsewhere. Non-monetary burn-rate indicators are outside scope.

## Capabilities
### Modified Capabilities
- `provider-request-log-attribution`: plain monetary subtotal formatting.

## Impact
Frontend shared cost formatter and regression tests only; no pricing, accounting, storage or production changes.
