# Account subscription end date

## Why

Some accounts are known to stop at a fixed point: a cancelled Codex or Claude
subscription, or an Antigravity trial that is not renewed. Neither OpenAI nor
Anthropic reports a cancellation date that codex-lb can read, so the
projections assume each account refills at every reset forever. Near the end
date this overstates runway: the weekly pace counts relief that will never
arrive, and the remaining quota that is lost at the end is counted as usable.

## What Changes

- Codex, Claude and Antigravity accounts gain an optional subscription end
  (date and time, stored in UTC). A dashboard API lists and sets it; OpenRouter
  and OpenAI-compatible accounts, which have no subscription window, reject it.
- Each Codex, Claude and Antigravity account detail shows a Subscription end
  panel after the Note panel, with a date-time editor for writers.
- The weekly pace treats an end date as a capacity cutoff: the account is
  inactive once it has ended; before that, its linear schedule ends at the
  end date, its later resets bring no relief, its remaining quota is lost at
  the end in the runway and depletion forecasts, and it counts only for its
  remaining share of the next seven days in the add-capacity estimate. The
  pace response lists upcoming ends, and the runway timeline marks them.
- The Codex 5-hour and weekly depletion projections use the end as the
  window's horizon when it comes before the reset, and skip ended accounts.

## Impact

- Migration adding a nullable `subscription_ends_at` column to `accounts`
  and `model_sources`.
- New `/api/account-subscriptions` endpoints.
- Weekly pace core and its Codex, Claude and Antigravity builders; Codex
  depletion; weekly pace card timeline; three account details.
- Routing and the quota planner are unchanged: the end date informs
  projections only.
