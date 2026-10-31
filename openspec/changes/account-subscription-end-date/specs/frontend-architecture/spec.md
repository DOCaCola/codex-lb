## ADDED Requirements

### Requirement: Account subscription end date
Codex, Claude and Antigravity accounts SHALL support an optional subscription
end, a date and time stored in UTC. `GET /api/account-subscriptions` SHALL list
the set end dates for readers of accounts, and
`PUT /api/account-subscriptions/accounts/{account_id}` or
`PUT /api/account-subscriptions/model-sources/{source_id}` SHALL set or clear
one for account writers. A timezone-less end SHALL be rejected. Setting an end on
an OpenRouter or OpenAI-compatible account SHALL fail with
`subscription_end_not_applicable`. The Codex, Claude and Antigravity account
details SHALL show a Subscription end panel after the Note panel, stating the
end in the dashboard's date format with the time remaining, or that it has
ended; writers SHALL be able to set it in local time, change it or clear it.
The end date SHALL NOT affect routing.

#### Scenario: Set an end date
- **WHEN** a writer sets 15 November 2026 18:00 local time on a Claude account
- **THEN** the account stores that instant in UTC and its detail shows it with the time remaining

#### Scenario: Clear an end date
- **WHEN** a writer clears the end date
- **THEN** the account has no end date and projections treat it as renewing

#### Scenario: Not applicable
- **WHEN** an end date is set on an OpenRouter account
- **THEN** the API returns 400 `subscription_end_not_applicable`

#### Scenario: Unknown account
- **WHEN** an end date is set for an account ID that does not exist
- **THEN** the API returns 404 `account_not_found`

### Requirement: Quota projections honor subscription end dates
The weekly pace for Codex, Claude and every Antigravity family SHALL treat an
account's subscription end as a capacity cutoff:

- An account whose end has passed SHALL count as inactive and SHALL NOT be pooled.
- When the end comes before the account's next weekly reset, its expected
  remaining and scheduled burn SHALL follow a linear schedule from the window
  start to the end, so the plan spends the account by its end.
- Resets at or after the end SHALL NOT count as relief, as reset events, or as
  refills in the forecast simulation; at the end the account's remaining
  balance SHALL be removed from the pool.
- The forecast and the depletion ETA SHALL spend the balance that expires
  first, by reset or end, before later balances.
- When no pooled account resets before its end, there SHALL be no next relief,
  and a depletion ETA SHALL make the verdict `runs_dry`.
- The add-capacity estimate SHALL count each account's capacity only for the
  share of the next seven days before its end.
- The response SHALL list each end within the next seven days with the
  account's weekly capacity, and the runway timeline SHALL mark it distinctly
  from resets.

The Codex 5-hour and weekly depletion projections SHALL use the end as the
window's horizon when it precedes the reset, measuring the safe line from the
window start to the end, and SHALL skip accounts whose end has passed.

#### Scenario: Ending account brings no relief
- **GIVEN** a Codex account at 100% weekly usage whose subscription ends a day before its reset
- **WHEN** the weekly pace is computed
- **THEN** that reset is neither the next relief nor a reset event, and an end marker is listed instead

#### Scenario: Remaining quota lapses at the end
- **GIVEN** two accounts with equal remaining quota, one ending in 10 hours
- **WHEN** the depletion ETA is computed at a burn rate that spends half of one account's remaining quota in 10 hours
- **THEN** the ending account's balance is spent first and its unspent half is removed at the end, shortening the ETA compared with no end date

#### Scenario: Ended account is inactive
- **WHEN** an account's subscription end has passed
- **THEN** the weekly pace excludes it and counts it as inactive

#### Scenario: No end dates
- **WHEN** no account has an end date
- **THEN** every projection equals the projection without the feature
