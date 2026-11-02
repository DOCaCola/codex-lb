## ADDED Requirements

### Requirement: Dashboard limit bars show recent usage

Quota windows SHALL report the share of the window used recently: the last hour for windows of one day or less,
the last 24 hours for longer windows. The share SHALL be the current used percentage minus the latest recorded
reading at or before the start of that period. When the current window began inside the period, the whole current
used percentage SHALL count as recent. When no reading from inside the current window exists at or before the start
of the period, or the window has no reset time, the share SHALL be unknown. The share SHALL never be negative.

Dashboard limit bars SHALL draw a known, positive share as a faint tint of the account colour directly after the
remaining fill and SHALL state the share in the bar's tooltip. A browser-local Appearance setting SHALL turn the
tint on or off; it SHALL default to on.

#### Scenario: Usage within the last hour

- **WHEN** a 5h window reads 40% used now and 25% used one hour ago
- **THEN** the window reports 15% recent usage and the dashboard bar tints 15% after the remaining fill

#### Scenario: Window reset inside the period

- **WHEN** a 5h window reset 20 minutes ago and now reads 6% used
- **THEN** the window reports 6% recent usage

#### Scenario: No reading before the period

- **WHEN** a weekly window has no reading from the current window at or before 24 hours ago
- **THEN** the recent usage is unknown and no tint is drawn

#### Scenario: Tint turned off

- **WHEN** the Appearance setting for recent usage is off
- **THEN** dashboard limit bars show only the remaining fill and pace tick
