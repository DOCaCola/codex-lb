# Context: dashboard "Coming up"

## Purpose

The section answers one question at a glance: what changes my capacity next, and when. It is the dashboard version
of the "Coming up" list in the desktop usage popover, with one difference: the dashboard is the operator's view, so
rows name individual accounts.

## Sources

Everything comes from queries the page already runs.

- Account summaries (`summarizeSources` with both windows): status, the cooldown end of a limited account
  (`notice.until`), and each window's percentage left and reset time.
- Subscription ends (`useAccountSubscriptionEnds`, already part of the summary context).
- Pool paces: `weeklyCreditPace` (Codex), `claudeWeeklyPace`, and one `antigravityWeeklyPace` per model family.
  `resetEvents` gives the credits each account's weekly reset returns, `depletionEtaHours` with
  `runwayStatus === "runs_dry"` the projected run-out, `lapsingCredits` with `lapseInHours` the quota the
  recent burn would leave unspent when subscriptions end, and `subscriptionEnds` the weekly credits each end removes.

Pace hours are relative to the moment the page renders, the same convention as the pace card's runway.

## Decisions

- Events at most 60 seconds apart count as simultaneous. Reset times from the pace and from account windows come
  from the same stored reset, so they match well within that.
- A limited account whose cooldown ends at the moment of a pool reset shows one "back" row carrying the credits that
  reset returns.
- Weekly resets of windows with 80% or more left, and refills of windows with 20% or more left, are left out as
  noise. Refills are listed only for active accounts; a limited account's return already has its own row.
- Run-outs and lapses are forecasts from the recent burn rate and are marked with "~".
- OpenRouter and OpenAI-compatible sources have no timed capacity events and do not appear.
- The list shows eight rows before "Show all". The 7d horizon groups rows under day headings.

## Example

At 13:15 with one Claude account (5h window 2% left, resets 13:40; weekly 10% left, projected to run dry at 18:18,
resets 23:00) and a limited Codex account whose weekly window resets at 20:52, the 24h list reads:

| Time | Row | Impact |
| --- | --- | --- |
| 13:40 | Claude account · 5h refills from 2% left | 2% → 100% |
| ~18:18 | Claude pool may run dry at the current pace | |
| 20:52 | Codex account back · Weekly resets | +36.8k credits · 46% of pool |
| 23:00 | Claude account · Weekly resets | +0.9 Pro · 90% of pool |
