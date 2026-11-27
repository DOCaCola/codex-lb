## MODIFIED Requirements

### Requirement: Grouped account enrollment
The add-account chooser SHALL list the subscription providers Codex, Claude and Antigravity first, each with OAuth
and file import, followed by the API providers OpenAI API, OpenRouter and OpenAI-compatible in that order. The
OpenAI API and OpenRouter options SHALL take an API key; the OpenAI-compatible option SHALL take an API endpoint.
Optional providers SHALL be absent when unavailable. All options SHALL share icon sizing, alignment and focus
styling, and preserve close-before-open action handoff.

#### Scenario: All providers available
- **WHEN** an operator opens the account chooser with all providers available
- **THEN** Codex, Claude and Antigravity appear first, followed by OpenAI API, OpenRouter and OpenAI-compatible

#### Scenario: Optional provider unavailable
- **WHEN** a provider has no enrollment callback
- **THEN** its option is not rendered
