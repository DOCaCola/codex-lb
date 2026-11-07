## ADDED Requirements

### Requirement: Dashboard lists upcoming capacity events

A "Coming up" section between the dashboard's Accounts and Activity sections SHALL list, by time, the events within
the horizon that change Codex, Claude or Antigravity capacity: a limited account's return, a weekly pool reset, an
active account's window with less than 20% left refilling, a projected run-out ("runs dry" verdict), credits left
unspent when subscriptions end ("lapses" verdict), and a subscription end. Run-outs and lapses SHALL be marked as
estimates.

#### Scenario: Projected run-out

- **WHEN** the Claude pool pace reports "runs dry" with a depletion estimate five hours away
- **THEN** a row five hours from now, marked as an estimate, says the Claude pool may run dry at the current pace

#### Scenario: Barely used window

- **WHEN** an active account's 5h window has 60% left and resets within the horizon
- **THEN** the section lists no refill for it

#### Scenario: Subscription end

- **WHEN** an account's subscription ends in three days and the horizon is seven days
- **THEN** a row at that moment says the account's subscription ends and shows the weekly credits it removes

### Requirement: Upcoming events merge and name accounts

A pool reset SHALL name the account whose window resets within 60 seconds of it and SHALL be left out when that
window has 80% or more left. A pool reset at a limited account's return SHALL merge into that return. Events of the
same kind, provider, pool and window within 60 seconds SHALL share one row. Account names SHALL link to the account
and SHALL follow the account list's privacy blur.

#### Scenario: Limited account comes back with its weekly reset

- **WHEN** a limited Codex account's cooldown ends at 20:52 and the Codex pool pace has a reset returning 36,800
  credits at 20:52
- **THEN** one row at 20:52 says the account is back as its weekly window resets and shows +36.8k credits

#### Scenario: Simultaneous returns

- **WHEN** three limited Codex accounts' 5h windows reset within the same minute
- **THEN** one row lists all three accounts as back

### Requirement: Upcoming events horizon

The section SHALL offer a 24-hour and a 7-day horizon, defaulting to 24 hours, and SHALL remember the choice in the
browser. The 7-day horizon SHALL group rows under day headings. The section SHALL show at most eight rows until the
operator asks for all, and SHALL say so when nothing is scheduled within the horizon.

#### Scenario: Horizon choice

- **WHEN** the operator selects 7d
- **THEN** events up to seven days ahead appear under day headings, and the dashboard opens with 7d next time

#### Scenario: Nothing scheduled

- **WHEN** no event falls within the horizon
- **THEN** the section says nothing is scheduled in the next 24 hours or 7 days
