## MODIFIED Requirements

### Requirement: Quota projections honor subscription end dates
The weekly pace for Codex, Claude and every Antigravity family SHALL treat an
account's upcoming subscription end as a capacity cutoff. An end that has
passed SHALL be ignored, so the account is projected as renewing:

- When the end comes before the account's next weekly reset, its expected
  remaining and scheduled burn SHALL follow a linear schedule from the window
  start to the end, so the plan spends the account by its end.
- Resets at or after the end SHALL NOT count as relief, as reset events, or as
  refills in the forecast simulation; at the end the account's remaining
  balance SHALL be removed from the pool.
- The forecast and the depletion ETA SHALL spend the balance that expires
  first, by reset or end, before later balances.
- When no pooled account resets before its end, there SHALL be no next relief,
  and a depletion ETA SHALL make the verdict `runs_dry`. Balances that end
  unspent SHALL NOT count as depletion: when every balance ends before the
  recent burn spends it, there SHALL be no depletion ETA.
- For accounts whose end comes before their next reset, the response SHALL
  report the quota the recent burn leaves unspent at those ends, spending the
  balance that expires first and refilling renewing accounts at their resets,
  the hours until the first end that leaves quota behind, and the steady spend
  on the ending accounts that leaves nothing behind at any of their ends.
- When that unspent quota is at least 5% of the pool and the verdict is
  neither `runs_dry` nor tight by margin to relief, the verdict SHALL be
  `lapses`, ahead of tight by low headroom.
- The add-capacity estimate SHALL count each account's capacity only for the
  share of the next seven days before its end. The Claude and Antigravity
  paces SHALL NOT report it.
- The response SHALL list each end within the next seven days with the
  account's weekly capacity, and the runway timeline SHALL mark it distinctly
  from resets.

With the `lapses` verdict the weekly pace card SHALL show "Unused at end" with
the unspent amount, the time until the end and the use-up rate instead of a
depletion ETA.

The Codex 5-hour and weekly depletion projections SHALL use the end as the
window's horizon when it precedes the reset, measuring the safe line from the
window start to the end.

#### Scenario: Ending account brings no relief
- **GIVEN** a Codex account at 100% weekly usage whose subscription ends a day before its reset
- **WHEN** the weekly pace is computed
- **THEN** that reset is neither the next relief nor a reset event, and an end marker is listed instead

#### Scenario: Remaining quota lapses at the end
- **GIVEN** two accounts with equal remaining quota, one ending in 10 hours
- **WHEN** the depletion ETA is computed at a burn rate that spends half of one account's remaining quota in 10 hours
- **THEN** the ending account's balance is spent first and its unspent half is removed at the end, shortening the ETA compared with no end date

#### Scenario: Ending pool with spare quota
- **GIVEN** a single Claude Max account at 0% weekly usage whose subscription ends in 15 hours, before its reset
- **WHEN** the recent burn would spend about 0.75 of its 5 Pro units by the end
- **THEN** there is no depletion ETA, the verdict is `lapses` with about 4.25 Pro units unspent in 15 hours
- **AND** the use-up rate is 5 Pro units over 15 hours

#### Scenario: Passed end is ignored
- **WHEN** an account's subscription end has passed and the account keeps serving requests
- **THEN** the account's status and routing are unchanged
- **AND** the weekly pace and depletion project it as a renewing account

#### Scenario: No end dates
- **WHEN** no account has an end date
- **THEN** every projection equals the projection without the feature
