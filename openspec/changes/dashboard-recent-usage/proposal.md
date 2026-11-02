# Show recent usage on dashboard limit bars

## Why

A dashboard limit bar shows only what is left. Two accounts at 40% look the same whether one has been idle all
day or just spent half its window in the last hour. Operators need to see, at a glance, which accounts are being
drained right now.

## What Changes

- Quota windows report how much of the window was used recently: the last hour for 5h windows, the last 24 hours
  for weekly windows. Codex accounts report it in the dashboard overview; Claude and Antigravity windows report it
  in their account payloads. It is computed from the quota history already recorded; no new upstream requests.
- Dashboard limit bars (cards and list) draw that share as a faint tint of the account colour directly after the
  remaining fill, with the figure in the bar's tooltip.
- A browser-local Appearance setting turns the tint on or off (default on).

## Impact

- Specs: `account-quota-presentation`.
- Backend: `app/core/usage/recent.py`, Codex account mapper and dashboard service, Claude and Antigravity quota status.
- Frontend: dashboard limit bars, provider summaries, Appearance settings.
