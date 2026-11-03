# Show a subscription end only when it matters

## Why

Account cards show a manually set subscription end as soon as it is entered, even when it is weeks away and
outside the quota cycle the card describes. The notice then occupies the strip without telling the operator
anything that affects the current cycle.

## What Changes

- The subscription end notice appears only when the end falls inside the account's running quota cycle, which
  ends at its weekly reset (monthly reset for monthly-only accounts), or when it is at most three days away.
- Accounts without a weekly or monthly window use only the three-day lead.
- Projections and the account detail panel are unchanged.

## Impact

- Frontend: `frontend/src/features/accounts/provider-summary.ts` and its tests.
- Spec: `frontend-architecture`, requirement "Account notices show the time left".
