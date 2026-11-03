# Show recent usage on dashboard limit bars

## Why

A dashboard limit bar shows only what is left. Two accounts at 40% look the same whether one has been idle all
day or just spent half its window in the last hour. Operators need to see, at a glance, which accounts are being
drained right now.

## What Changes

- Quota windows report how much of the window was used recently. The period is chosen per browser: 15 minutes,
  30 minutes or 1 hour for 5h windows (default 1 hour); 1, 2, 4, 6, 12 or 24 hours, or today since local midnight,
  for weekly windows (default 24 hours). Codex accounts report it in the dashboard overview; Claude and Antigravity
  windows report it in their account lists. It is computed from the quota history already recorded; no new upstream
  requests.
- Dashboard limit bars (cards and list) draw that share as a faint tint of the account colour directly after the
  remaining fill, with the figure in the bar's tooltip.
- Browser-local Appearance settings turn the tint on or off (default on) and choose the two periods.

## Impact

- Specs: `account-quota-presentation`.
- Backend: `app/core/usage/recent.py`, Codex account mapper and dashboard service, Claude and Antigravity quota status.
- Frontend: dashboard limit bars, provider summaries, Appearance settings.
