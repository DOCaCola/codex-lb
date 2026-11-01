## MODIFIED Requirements

### Requirement: Countdowns coarsen with the time left

Every reset and expiry countdown SHALL round down and show at least one minute. It SHALL show minutes only below one
hour, hours and minutes below one day, also when the minutes are zero, and days and hours from one day on, also when
the hours are zero. Cooldowns, the 5-hour, weekly and API key limit windows coming back, SHALL keep days and hours
however far away. Expiries, a subscription end or a reset credit running out, SHALL show days only from three days
left. Elapsed durations, such as a conversation's Lasted value, are not countdowns.

#### Scenario: Three days or more
- **WHEN** a weekly quota resets in 6 days 13 hours
- **THEN** its countdown reads `in 6d 13h`
- **WHEN** a subscription ends in 6 days 13 hours
- **THEN** its countdown reads `in 6d`

#### Scenario: Between one and three days
- **WHEN** a quota resets in 2 days 23 hours
- **THEN** its countdown reads `in 2d 23h`

#### Scenario: Below one day
- **WHEN** a quota resets in exactly 7 hours
- **THEN** its countdown reads `in 7h 0m`

#### Scenario: Below one hour
- **WHEN** a quota resets in 42 minutes
- **THEN** its countdown reads `in 42m`

