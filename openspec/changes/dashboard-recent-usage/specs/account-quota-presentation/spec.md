## ADDED Requirements

### Requirement: Dashboard limit bars show recent usage

Quota windows SHALL report the share of the window used during a recent period. Windows of one day or less SHALL use
the short period: 15, 30 or 60 minutes, default 60. Longer windows SHALL use the long period: 60, 120, 240, 360, 720
or 1440 minutes, default 1440, or a period starting at a given instant no more than 25 hours ago, which the dashboard
uses for the browser's local midnight. The Codex dashboard overview and the Claude and Antigravity account lists SHALL
accept the periods as request parameters and SHALL reject any other value, or both forms of long period at once,
with a validation error.

The share SHALL be the current used percentage minus the latest recorded reading at or before the start of that
period. When the current window began inside the period, the whole current used percentage SHALL count as recent.
When no reading from inside the current window exists at or before the start of the period, or the window has no
reset time, the share SHALL be unknown. The share SHALL never be negative.

Dashboard limit bars SHALL draw a known, positive share as a faint tint of the account colour directly after the
remaining fill and SHALL state the share and its period in the bar's tooltip. Browser-local Appearance settings SHALL
turn the tint on or off, defaulting to on, and SHALL choose the short and long periods, including Today for the long
period.

#### Scenario: Usage within the last hour

- **WHEN** a 5h window reads 40% used now and 25% used one hour ago
- **THEN** the window reports 15% recent usage and the dashboard bar tints 15% after the remaining fill

#### Scenario: Chosen periods

- **WHEN** the operator chooses 30 minutes for 5h limits and 6 hours for weekly limits
- **THEN** 5h windows report usage since 30 minutes ago, weekly windows report usage since 6 hours ago, and the
  tooltips name those periods

#### Scenario: Weekly usage today

- **WHEN** the operator chooses Today for weekly limits
- **THEN** weekly windows report usage since the browser's local midnight and the tooltip says it was used today

#### Scenario: Unsupported period

- **WHEN** a request asks for a 45-minute short period, or for both a long period in minutes and a start instant
- **THEN** the request is rejected with a validation error

#### Scenario: Window reset inside the period

- **WHEN** a 5h window reset 20 minutes ago and now reads 6% used
- **THEN** the window reports 6% recent usage

#### Scenario: No reading before the period

- **WHEN** a weekly window has no reading from the current window at or before 24 hours ago
- **THEN** the recent usage is unknown and no tint is drawn

#### Scenario: Tint turned off

- **WHEN** the Appearance setting for recent usage is off
- **THEN** dashboard limit bars show only the remaining fill and pace tick
