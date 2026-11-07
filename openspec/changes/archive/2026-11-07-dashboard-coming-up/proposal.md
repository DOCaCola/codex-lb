# Show what is coming up on the dashboard

## Why

The dashboard shows how much quota is left right now, but the moments that change it are scattered: a limited
account's return sits in its card notice, weekly resets are ticks on the pace card's runway, a projected run-out is
one line of that card, and subscription ends live on the account detail page. An operator who wants to know "when do I
get capacity back, and when do I lose it" has to read every card.

## What Changes

- A "Coming up" section between Accounts and Activity lists the next events that change capacity, ordered by time:
  limited accounts coming back, weekly pool resets, low windows refilling, projected run-outs, credits that would
  lapse unspent, and subscription ends.
- A 24h / 7d toggle chooses the horizon; the choice is stored in the browser.
- Simultaneous events of the same kind for the same pool merge into one row. Account names link to the account and
  honour privacy blur. Estimates are marked with "~".
- The section uses only data the dashboard already loads; no backend change.

## Impact

- Specs: `frontend-architecture`.
- Frontend: dashboard page, a new event builder and section component, dashboard preferences, shared amount and
  short-time formatters, locale files.
