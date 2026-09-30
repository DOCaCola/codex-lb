## ADDED Requirements

### Requirement: Optional model-specific quota presentation
Claude quota responses SHALL omit null Opus/Sonnet weekly windows when a successful retained usage snapshot establishes they were not reported. Shared windows SHALL retain unknown states when unavailable. Before any successful usage snapshot, scoped windows MAY remain unknown. Known scoped observations SHALL remain visible under stale, expired or reset-barrier states. Missing scoped windows MUST NOT imply model unavailability, unlimited entitlement or shared-quota duplication.

#### Scenario: Pro account without scoped windows
- **WHEN** a successful usage response includes shared windows and null model-specific windows
- **THEN** account details show the shared limits without unknown Opus/Sonnet quota rows

#### Scenario: Previously reported scoped quota is stale
- **WHEN** a scoped observation exists but a subsequent refresh fails
- **THEN** that observation remains visible as stale rather than disappearing
