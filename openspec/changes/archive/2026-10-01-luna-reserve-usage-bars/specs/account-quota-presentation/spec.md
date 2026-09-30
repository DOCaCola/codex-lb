## ADDED Requirements

### Requirement: Luna Reserve uses additional-quota bars without granting routing permission

Account usage refresh SHALL explicitly request Reserve-capable usage telemetry. Account details SHALL display reported `gpt-reserve` quota windows using the existing additional-quota fill-bar layout and reset countdowns. The display MUST distinguish missing percentages, unavailable Reserve and stale observations, MUST NOT infer percentages from availability, and MUST NOT create Reserve model catalog entries or routing authorization. Ordinary Codex and Spark quota behavior MUST remain unchanged.

#### Scenario: Reserve windows have percentages
- **WHEN** an authenticated account usage response reports Reserve primary and secondary windows
- **THEN** account details display Luna Reserve bars with the reported window labels, percentages and reset countdowns
- **AND** 5h and weekly windows are side by side like ordinary usage, stacking on narrow screens
- **AND** Reserve does not enter ordinary usage totals or model admission

#### Scenario: Availability is not a percentage
- **WHEN** Reserve is reported with an availability flag but without percentage windows
- **THEN** the display states unknown usage without manufacturing an empty or full bar

#### Scenario: Reserve is denied or stale
- **WHEN** upstream denies Reserve or its retained observation exceeds the existing usage freshness horizon
- **THEN** the display identifies it as unavailable or unknown respectively
- **AND** stale observations do not display current percentage bars

#### Scenario: Capability and account binding
- **WHEN** account usage refresh queries upstream, including after credential refresh
- **THEN** it sends the Reserve capability header with the selected account's authentication
- **AND** passive reset-credit queries do not opt in
- **AND** mismatching upstream account/user identity does not update Reserve telemetry
