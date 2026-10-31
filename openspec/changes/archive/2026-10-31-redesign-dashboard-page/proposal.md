## Why

The dashboard spends its first screen on a page subtitle, two donut panels and a row of large stat cards before any
account appears. Account cards differ by provider, place warnings between the quota rows so charts of neighbouring
cards don't line up, show a 5h row for accounts that only have a weekly limit, and use coarse reset countdowns
("2h"). The list view repeats the Accounts page with sortable warm-up and credit columns. Top consumers show a cost
but no sense of whether a key is still active.

## What Changes

- A compact header: title, a one-sentence account health line (how many accounts can take work, which are limited
  and when the first comes back, how many are paused or need sign-in, the next 5-hour reset) and a refresh button.
  The page subtitle is removed.
- Quota: a Codex / Claude / Antigravity switch over three cards. Remaining credits (or quota) shows a 5-hour and a
  weekly ring with a per-account table and totals; Weekly pace and Top consumers keep their content. Each top
  consumer gets a two-hour cost sparkline from twelve ten-minute buckets (`costBuckets`) supplied by the overview
  and projections payloads.
- Accounts: one card for every provider. A card shows its identity, plan, today's cost and its limits, weekly
  first, with one row per window the account actually has. A coloured status strip with its remedy (Re-auth,
  Resume, Reset) appears at the bottom only when the account needs attention; Codex cards end with subscription and
  purchased credits and the reset-credit button. The header hint counts total, ready, limited, paused and
  sign-in accounts. The list view shows account, status, two limit meters and today's cost, without sort or
  warm-up columns.
- Activity: the five stat cards become one strip under the accounts, with the 1d / 7d / 30d switch beside its
  header. Account burn shows the weekly figure with the 5-hour figure as meta.
- Reset countdowns use two units ("2h 34m", "3d 4h").
- OpenRouter summaries list "All models" or the selected model count, like Claude, instead of a subtitle.
- Removed: the donut panels, stat grid, per-provider dashboard card components, the account list sort preference
  and the overview timeframe select.

## Impact

- Affected specs: `frontend-architecture`
- Affected code: `app/modules/dashboard`, `app/core/usage/coverage.py`, `frontend/src/features/dashboard`,
  provider account display components, formatters, dashboard preferences, translations
