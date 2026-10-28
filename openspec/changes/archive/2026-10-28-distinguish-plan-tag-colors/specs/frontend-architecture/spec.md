## ADDED Requirements

### Requirement: Distinct request-log plan tag colors

Request-log plan badges MUST assign distinct colors to `free`, `plus`, `prolite`, `pro`, `team`, `business`, `enterprise`, `edu`, `max`, `max_5x`, and `max_20x` in both light and dark themes. The same plan key MUST use the same palette across providers while preserving provider-specific labels. The recognized rate-limit metadata keys `guest`, `go`, `free_workspace`, `education`, `quorum`, and `k12` MUST also have explicit distinct colors when displayed. Badge text MUST have at least 4.5:1 contrast against its background in normal and hovered states in both themes.

#### Scenario: Previously aliased tiers appear together
- **WHEN** Pro, Max, Max 5×, Max 20×, Team, and Enterprise appear in a request table
- **THEN** each tier has its own text, background, and border colors
- **AND** the colors remain distinct when the dashboard theme changes

#### Scenario: Unknown tiers are not presented as Free
- **WHEN** a request snapshot contains `unknown` or an unrecognized nonempty plan key
- **THEN** its existing label is retained with neutral colors distinct from Free

#### Scenario: Missing snapshots remain missing
- **WHEN** a request has a null or blank plan snapshot
- **THEN** its plan cell displays `--` without a plan badge

#### Scenario: Same key across providers
- **WHEN** Codex Pro and Claude Pro requests appear together
- **THEN** their plan badges use identical theme colors
- **AND** each retains its existing display label
