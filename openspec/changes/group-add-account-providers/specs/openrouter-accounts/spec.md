## ADDED Requirements
### Requirement: Grouped account enrollment
The add-account chooser SHALL group actions under Codex, Claude and OpenRouter
in that order. Codex SHALL offer OAuth and file import. Optional provider groups
SHALL be absent when unavailable. All options SHALL share icon sizing, alignment
and focus styling, and preserve close-before-open action handoff.

#### Scenario: All providers available
- **WHEN** an operator opens the account chooser with all providers available
- **THEN** Codex options appear first, followed by Claude and OpenRouter groups

#### Scenario: Optional provider unavailable
- **WHEN** a provider has no enrollment callback
- **THEN** its group is not rendered
