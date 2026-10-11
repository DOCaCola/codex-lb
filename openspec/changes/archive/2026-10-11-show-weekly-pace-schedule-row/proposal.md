## Why
The runway redesign removed the comparison of actual weekly usage with the straight-line schedule, so the card no longer shows whether usage is ahead of or behind an even weekly spread. The backend still computes the scheduled and smoothed fields. The card's recommendations (throttle, pause, add accounts) are advice the operator does not want from the dashboard.

## What Changes
- The runway card for Codex and Claude gains a neutral schedule row: Used now, Scheduled by now, the smoothed gap (over, below, On pace), a bar with a schedule marker, and the smoothed over-schedule amount in the provider's unit. Wording reuses the previous card's strings.
- Over-schedule amount strings take a unit-aware amount, so Claude reads Pro units instead of credits.
- Both card layouts drop the Recommendations section entirely.

## Capabilities
### Modified Capabilities
- `frontend-architecture`: weekly pace card schedule row and recommendations.

## Impact
Frontend only. The dashboard API, including the throttle, pause and `addProAccounts` fields, is unchanged.
