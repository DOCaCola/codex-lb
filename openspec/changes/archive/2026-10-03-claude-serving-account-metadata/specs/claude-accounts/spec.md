## MODIFIED Requirements

### Requirement: Synthesized identity coherence
Translated Messages SHALL include a stable local device identity and the same scoped session identity in body metadata and headers. Session metadata on every outbound Messages request that carries it SHALL name the authenticated provider account UUID of the serving account; a client-supplied account UUID MUST NOT be forwarded to another account, and an unauthenticated account identity MUST NOT be fabricated. The provider account UUID SHALL be persisted from the authenticated profile and checked against the enrolled identity before use. Synthesized OS and architecture SHALL match the runtime; native reviewed headers SHALL remain caller-owned. No billing fingerprint SHALL be synthesized.

#### Scenario: Rotated credentials
- **WHEN** the selected account refreshes its token within the same client conversation
- **THEN** local device and session metadata remain stable without reusing identity across another client or account

#### Scenario: Pooled native request
- **WHEN** a native Claude Code request carrying its own account UUID is served by a different pooled account
- **THEN** the outbound metadata names the serving account's UUID and preserves the remaining client metadata

#### Scenario: Account enrolled before UUID persistence
- **WHEN** an enrolled account without a stored provider UUID next uses its credentials
- **THEN** its authenticated profile is checked against the enrolled identity and the UUID is stored, or the request fails if the identity differs

## ADDED Requirements

### Requirement: Claude extra usage presentation
Claude cards and account-list rows SHALL show a warning badge, in existing badge styling, when Anthropic usage data reports extra usage as enabled. The badge SHALL be absent when extra usage is disabled or unreported.

#### Scenario: Extra usage enabled
- **WHEN** the latest usage data reports extra usage enabled for an account
- **THEN** its card and list row show an extra-usage badge explaining that requests beyond subscription limits are billed
