## MODIFIED Requirements

### Requirement: Account notices show the time left

A notice that ends at a known time, such as an exhausted quota window or a subscription end, SHALL carry that time.
The dashboard card strip and the dashboard list row SHALL show the notice headline followed by the time left until it
ends, formatted like the limit-row reset times.

An upcoming subscription end SHALL produce a notice only when it falls at or before the end of the account's running
quota cycle, or when it is at most three days away. The running cycle ends at the weekly reset; for Codex accounts with
only a monthly window it ends at the monthly reset, and for Antigravity accounts at the latest weekly reset across
their quota families. An account without a known future cycle end SHALL use only the three-day lead.

#### Scenario: Exhausted weekly window
- **WHEN** an account's weekly window is exhausted and resets in 2 days 23 hours
- **THEN** its strip shows `Weekly limit · back in 2d 23h`

#### Scenario: Subscription end
- **WHEN** an account's subscription ends in 7 hours
- **THEN** its strip shows `Subscription ends in 7h 0m`

#### Scenario: Subscription end inside the running cycle
- **WHEN** an account's subscription ends in 4 days and its weekly quota resets in 5 days
- **THEN** its strip shows the subscription end

#### Scenario: Subscription end after the running cycle
- **WHEN** an account's subscription ends in 4 days and its weekly quota resets in 1 day
- **THEN** its strip does not show the subscription end
- **WHEN** the same subscription end is three days away
- **THEN** its strip shows the subscription end

#### Scenario: Account without a weekly or monthly window
- **WHEN** an account with only a 5-hour window has a subscription ending in 4 days
- **THEN** its strip does not show the subscription end until it is three days away
