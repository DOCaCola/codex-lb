## Why

A Claude Max account with a set subscription end showed "Runs dry" and "runs out
in ~15h" at 0% weekly usage. The depletion ETA treated the end of the pool's last
subscription as depletion, so quota that will go unused read as a shortage. The
operator needs the opposite signal: how much quota will lapse and what pace
spends it before the end.

The Claude and Antigravity paces also fed a hidden add-capacity estimate that
weighted a whole week of history at the account's current plan, inflating it
after plan changes (11 Pro accounts for about 6 Pro weeks of demand).

## What Changes

- A pool whose capacity all ends unspent has no depletion ETA.
- New runway verdict `lapses` when the recent burn leaves at least 5% of the pool
  unspent at subscription ends in their current window; it outranks low
  headroom but not depletion or a tight margin to relief.
- The pace response reports the lapsing quota, the hours to the first end that
  leaves quota behind, and the steady spend on ending accounts that uses them up.
- The weekly pace card shows "Unused at end" with the unspent amount, the time
  to the end, and the use-up rate.
- Claude and Antigravity paces no longer compute the add-capacity estimate.

## Impact

- Backend: `weekly_pace.py`, Claude and Antigravity pace builders, dashboard schemas.
- Frontend: weekly pace card, Antigravity tightest-family ranking, locales.
